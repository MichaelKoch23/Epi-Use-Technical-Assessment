import createClient, { type Middleware } from 'openapi-fetch'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './auth'
import type { paths } from './api-types'

export const apiClient = createClient<paths>({ baseUrl: '' })

const AUTH_PATH_FRAGMENT = '/api/v1/auth/'

const requestClones = new Map<string, Request>()

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
  onError({ id }) {
    requestClones.delete(id)
  },
  async onResponse({ request, response, id }) {
    const clone = requestClones.get(id)
    requestClones.delete(id)

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
