function titleCase(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
}

export function nameFromEmail(email: string): { first: string; last: string } {
  const words = (email.split('@')[0] ?? '')
    .split(/[._\-+]+/)
    .map((word) => word.replace(/\d+/g, ''))
    .filter(Boolean)
  return { first: titleCase(words[0] ?? email), last: titleCase(words[1] ?? '') }
}
