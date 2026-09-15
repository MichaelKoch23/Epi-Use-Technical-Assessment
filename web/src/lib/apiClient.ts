import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './api-types'

const ACTOR_ID_STORAGE_KEY = 'ehm.actorId'

/**
 * Temporary stand-in for the session a real login flow will establish.
 * The API's own auth is currently the same kind of placeholder — an
 * X-Actor-Id header naming an existing app_user row, in lieu of the JWT
 * flow in §9.1 — so this mirrors that on the client until both sides are
 * replaced together.
 */
export function getActorId(): string | null {
  return localStorage.getItem(ACTOR_ID_STORAGE_KEY)
}

export function setActorId(id: string | null): void {
  if (id) {
    localStorage.setItem(ACTOR_ID_STORAGE_KEY, id)
  } else {
    localStorage.removeItem(ACTOR_ID_STORAGE_KEY)
  }
}

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const actorId = getActorId()
    if (actorId) request.headers.set('X-Actor-Id', actorId)
    return request
  },
}

// Paths in the generated spec already include the /api/v1 prefix, so the
// client's own base is just the page's origin (relative, same as the
// plain fetch calls elsewhere — see vite.config.ts's dev proxy note).
export const apiClient = createClient<paths>({ baseUrl: '' })
apiClient.use(authMiddleware)
