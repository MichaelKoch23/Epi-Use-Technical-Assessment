/** Triggers a browser download for a Blob already in memory - shared by
 * every "save this as a file" affordance (import's error report, the
 * employee CSV export, the org chart PNG export), none of which can use a
 * plain `<a href>` since the request needs a bearer token attached. */
export function triggerDownload(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
