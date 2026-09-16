import { useMemo } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import { employeeKeys, hierarchyKeys } from '@/lib/queryKeys'
import { fetchRoots, fetchSubtree } from './useOrgChartData'
import type { ChartEmployee } from './types'

export interface HierarchyTreeNode {
  employee: ChartEmployee
  children: HierarchyTreeNode[]
}

/**
 * The full hierarchy, independent of whatever the interactive chart has
 * lazily loaded or the user has collapsed — the nested-list view is a
 * first-class equivalent (§ accessibility: "not a fallback"), so it fetches
 * each root's entire subtree rather than being gated by chart state.
 */
export function useFullHierarchy() {
  const rootsQuery = useQuery({ queryKey: hierarchyKeys.roots(), queryFn: fetchRoots })
  const roots = useMemo(() => rootsQuery.data ?? [], [rootsQuery.data])

  const subtreeQueries = useQueries({
    queries: roots.map((root) => ({
      queryKey: employeeKeys.subtree(root.id, undefined),
      queryFn: () => fetchSubtree(root.id),
    })),
  })

  const isLoading = rootsQuery.isLoading || subtreeQueries.some((q) => q.isLoading)
  const isError = rootsQuery.isError || subtreeQueries.some((q) => q.isError)

  // See useOrgChartData's identical comment: `useQueries` hands back a new
  // array every render, so the memo below depends on this stable version
  // string rather than the array itself to avoid recomputing (and hence
  // building new tree objects) on every unrelated render.
  const subtreeQueriesVersion = subtreeQueries.map((q) => `${q.dataUpdatedAt}:${q.status}`).join('|')

  const tree = useMemo(() => {
    const childrenByManager = new Map<string, ChartEmployee[]>()
    roots.forEach((_root, i) => {
      const nodes = subtreeQueries[i]?.data ?? []
      for (const { employee } of nodes) {
        if (!employee.manager_id) continue
        if (!childrenByManager.has(employee.manager_id)) {
          childrenByManager.set(employee.manager_id, [])
        }
        childrenByManager.get(employee.manager_id)!.push(employee)
      }
    })

    const build = (employee: ChartEmployee): HierarchyTreeNode => ({
      employee,
      children: (childrenByManager.get(employee.id) ?? [])
        .slice()
        .sort((a, b) => a.last_name.localeCompare(b.last_name))
        .map(build),
    })

    return roots
      .slice()
      .sort((a, b) => a.last_name.localeCompare(b.last_name))
      .map(build)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roots, subtreeQueriesVersion])

  return { tree, isLoading, isError }
}
