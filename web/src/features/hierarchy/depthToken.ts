const DEPTH_TOKENS = [
  'border-l-depth-0',
  'border-l-depth-1',
  'border-l-depth-2',
  'border-l-depth-3',
  'border-l-depth-4',
] as const

export function depthToken(depth: number): (typeof DEPTH_TOKENS)[number] {
  return DEPTH_TOKENS[Math.min(Math.max(depth, 0), DEPTH_TOKENS.length - 1)]!
}
