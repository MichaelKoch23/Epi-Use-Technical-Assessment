import { QueryClient } from '@tanstack/react-query'

// 30s: short enough that HR data feels current, long enough that moving
// between the list, a detail drawer and back doesn't refetch for no
// reason. Individual queries can lower this where it actually matters.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
    },
  },
})
