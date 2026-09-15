// Gravatar now resolves by SHA-256 of the trimmed, lower-cased email (the
// legacy MD5 endpoint still works but is deprecated) — see the "Gravatar
// avatars" section of docs/brand_style_guide.html for the resolution order
// this backs: uploaded override, then Gravatar, then initials.
async function sha256Hex(input: string): Promise<string> {
  const bytes = new TextEncoder().encode(input)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

/**
 * `d=404` (rather than a mystery-person default) so a caller can `onError`
 * its way to the initials fallback instead of silently showing a stranger.
 */
export async function gravatarUrl(email: string, sizePx: number): Promise<string> {
  const hash = await sha256Hex(email.trim().toLowerCase())
  return `https://gravatar.com/avatar/${hash}?s=${sizePx}&d=404`
}
