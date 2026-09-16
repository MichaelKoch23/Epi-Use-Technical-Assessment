/** Best-effort message from a FastAPI error body - plain `{detail: string}`,
 * `application/problem+json` (`{detail, title}`), or 422's
 * `{detail: [{msg}, ...]}` - falling back to a generic message otherwise. */
export function getErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const messages = detail
        .map((entry) => (entry && typeof entry === 'object' && 'msg' in entry ? String(entry.msg) : null))
        .filter((msg): msg is string => Boolean(msg))
      if (messages.length > 0) return messages.join('; ')
    }
  }
  return fallback
}
