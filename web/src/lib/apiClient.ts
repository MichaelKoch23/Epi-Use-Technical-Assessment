import createClient, { type Middleware } from 'openapi-fetch'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './auth'
import type { paths } from './api-types'

// Paths in the generated spec already include the /api/v1 prefix, so the
// client's own base is just the page's origin (relative, same as the
// plain fetch calls elsewhere - see vite.config.ts's dev proxy note).
export const apiClient = createClient<paths>({ baseUrl: '' })

const AUTH_PATH_FRAGMENT = '/api/v1/auth/'

// A request that gets a 401 needs to be replayed with a fresh access
// token - but by the time `onResponse` sees it, the original `Request`'s
// body (if any) has already been streamed to the network and can't be
// read again. A clone taken in `onRequest`, before it's ever sent, is
// still untouched and safe to replay exactly once.
const requestClones = new Map<string, Request>()

// Concurrent 401s (e.g. several queries in flight at once) share one
// refresh call rather than each racing the server with their own.
let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = getRefreshToken()
      if (!refreshToken) return null
      try {
        const response = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        if (!response.ok) return null
        const data = (await response.json()) as { access_token: string; refresh_token: string }
        setTokens(data.access_token, data.refresh_token)
        return data.access_token
      } catch {
        return null
      }
    })()
  }
  try {
    return await refreshPromise
  } finally {
    refreshPromise = null
  }
}

function redirectToLogin() {
  clearTokens()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.assign('/login')
  }
}

const authMiddleware: Middleware = {
  onRequest({ request, id }) {
    requestClones.set(id, request.clone())
    const token = getAccessToken()
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  // `onResponse` never runs for a request that fails at the network layer
  // (offline, DNS failure, aborted), so the clone it would have removed
  // stays in the map holding its buffered body. `onError` is that path's
  // counterpart - without it, a flaky connection leaks one whole request
  // body per failure for as long as the tab stays open.
  onError({ id }) {
    requestClones.delete(id)
  },
  async onResponse({ request, response, id }) {
    const clone = requestClones.get(id)
    requestClones.delete(id)

    // Never intercept the auth endpoints themselves - a failed refresh
    // must surface as a failed refresh, not recurse into another one.
    if (response.status !== 401 || request.url.includes(AUTH_PATH_FRAGMENT)) {
      return response
    }

    const newToken = await refreshAccessToken()
    if (!newToken || !clone) {
      redirectToLogin()
      return response
    }

    clone.headers.set('Authorization', `Bearer ${newToken}`)
    return fetch(clone)
  },
}

apiClient.use(authMiddleware)
