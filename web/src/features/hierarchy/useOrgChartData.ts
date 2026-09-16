import { useCallback, useMemo, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import { employeeKeys, hierarchyKeys } from '@/lib/queryKeys'
import type { ChartEmployee } from './types'

// "fetch /hierarchy/roots plus two levels" - one subtree(depth=2) call per
// root returns the root itself (depth 0), its direct reports (depth 1) and
// their reports (depth 2) in a single request.
const INITIAL_DEPTH = 2
// Every lazy expand-on-demand fetch after that only needs the next level.
const EXPAND_DEPTH = 1

export async function fetchRoots(): Promise<ChartEmployee[]> {
  const { data, error } = await apiClient.GET('/api/v1/hierarchy/roots')
  if (error) throw error
  return data
}

/** `depth` omitted fetches the entire subtree (the server default), used by
 * the full-parity nested-list/print view rather than the chart's lazy load. */
export async function fetchSubtree(id: string, depth?: number) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/subtree', {
    params: { path: { employee_id: id }, query: { depth } },
  })
  if (error) throw error
  return data
}

async function fetchReportingLine(id: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/reporting-line', {
    params: { path: { employee_id: id } },
  })
  if (error) throw error
  return data
}

/** Thrown by the reassignment mutation on a 409, mirroring the employees
 * feature's `VersionConflict` (§5.4) - the chart surfaces it as a toast and
 * rolls the drag back rather than a conflict-resolution dialog. */
export class ChartVersionConflict extends Error {
  employeeId: string
  constructor(employeeId: string, message: string) {
    super(message)
    this.name = 'ChartVersionConflict'
    this.employeeId = employeeId
  }
}

/**
 * All org-chart data in one place: the lazily-loaded, per-node-cached
 * employee tree (§7.3 - "roots plus two levels initially, then a subtree
 * fetch on expand"), expand/collapse state, and manager reassignment with
 * an optimistic client-side override so a drag moves the card immediately
 * and rolls back on failure.
 */
export function useOrgChartData() {
  const queryClient = useQueryClient()

  const rootsQuery = useQuery({ queryKey: hierarchyKeys.roots(), queryFn: fetchRoots })
  const roots = useMemo(() => rootsQuery.data ?? [], [rootsQuery.data])

  const rootSubtrees = useQueries({
    queries: roots.map((root) => ({
      queryKey: employeeKeys.subtree(root.id, INITIAL_DEPTH),
      queryFn: () => fetchSubtree(root.id, INITIAL_DEPTH),
    })),
  })

  // Branches the user expanded past what the initial fetch covered, or
  // that a search/focus jump needed to pull in - each gets its own
  // independently cached, depth-1 subtree fetch (cache per node id).
  const [pendingExpandIds, setPendingExpandIds] = useState<Set<string>>(new Set())
  const expandQueries = useQueries({
    queries: [...pendingExpandIds].map((id) => ({
      queryKey: employeeKeys.subtree(id, EXPAND_DEPTH),
      queryFn: () => fetchSubtree(id, EXPAND_DEPTH),
    })),
  })

  // Ancestor employees pulled in by search/focus via /reporting-line -
  // merged into the known employee set even before their own subtree
  // (if any) has been fetched, so the connecting chain renders at once.
  const [extraEmployees, setExtraEmployees] = useState<Map<string, ChartEmployee>>(new Map())

  // User-collapsed branches. A node whose children are simply unknown yet
  // (not fetched) is *not* "collapsed" - it just has nothing to show below
  // it until its own expand fetch resolves.
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set())

  // Optimistic manager reassignment: overrides the fetched `manager_id`
  // for a node while a drag/keyboard reassignment is in flight, so the
  // card moves instantly; cleared on rollback or once the server refetch
  // has landed.
  const [managerOverrides, setManagerOverrides] = useState<Map<string, string | null>>(new Map())

  const isLoading = rootsQuery.isLoading || rootSubtrees.some((q) => q.isLoading)
  const isError = rootsQuery.isError || rootSubtrees.some((q) => q.isError)

  // `useQueries` returns a new array instance on every render regardless of
  // whether any query's data actually changed. Depending on that array
  // directly would make this memo - and everything downstream that reads
  // its Maps by reference (the chart's Dagre relayout effect included) -
  // recompute on every unrelated render, which turns into an infinite
  // relayout loop. These version strings only change when a query's data
  // or status genuinely does.
  const rootSubtreesVersion = rootSubtrees.map((q) => `${q.dataUpdatedAt}:${q.status}`).join('|')
  const expandQueriesVersion = expandQueries.map((q) => `${q.dataUpdatedAt}:${q.status}`).join('|')

  const { employeesById, childrenByManager, loadedIds } = useMemo(() => {
    const employeesById = new Map<string, ChartEmployee>()
    const childrenByManager = new Map<string, Set<string>>()
    const loadedIds = new Set<string>()

    for (const employee of extraEmployees.values()) {
      employeesById.set(employee.id, employee)
    }

    const ingest = (
      nodes: { employee: ChartEmployee; depth: number }[] | undefined,
      queriedId: string
    ) => {
      if (!nodes || nodes.length === 0) return
      for (const { employee } of nodes) {
        employeesById.set(employee.id, employee)
      }
      const maxDepth = Math.max(...nodes.map((n) => n.depth))
      for (const { employee, depth } of nodes) {
        if (depth < maxDepth) loadedIds.add(employee.id)
      }
      loadedIds.add(queriedId)
    }

    roots.forEach((root, i) => ingest(rootSubtrees[i]?.data, root.id))
    ;[...pendingExpandIds].forEach((id, i) => ingest(expandQueries[i]?.data, id))

    for (const employee of employeesById.values()) {
      const managerId = managerOverrides.has(employee.id)
        ? managerOverrides.get(employee.id)!
        : employee.manager_id
      if (!managerId) continue
      if (!childrenByManager.has(managerId)) childrenByManager.set(managerId, new Set())
      childrenByManager.get(managerId)!.add(employee.id)
    }

    return { employeesById, childrenByManager, loadedIds }
    // `rootSubtrees`/`expandQueries` are read inside via closure - see the
    // version-string comment above for why they're not listed directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roots, rootSubtreesVersion, pendingExpandIds, expandQueriesVersion, extraEmployees, managerOverrides])

  const depthById = useMemo(() => {
    const depths = new Map<string, number>()
    const queue: string[] = []
    for (const root of roots) {
      depths.set(root.id, 0)
      queue.push(root.id)
    }
    while (queue.length > 0) {
      const id = queue.shift()!
      const depth = depths.get(id)!
      for (const childId of childrenByManager.get(id) ?? []) {
        if (!depths.has(childId)) {
          depths.set(childId, depth + 1)
          queue.push(childId)
        }
      }
    }
    return depths
  }, [roots, childrenByManager])

  const visibleIds = useMemo(() => {
    const visible = new Set<string>()
    const queue = roots.map((root) => root.id)
    while (queue.length > 0) {
      const id = queue.shift()!
      if (visible.has(id)) continue
      visible.add(id)
      if (collapsedIds.has(id)) continue
      for (const childId of childrenByManager.get(id) ?? []) queue.push(childId)
    }
    return visible
  }, [roots, childrenByManager, collapsedIds])

  const hasChildren = useCallback(
    (id: string): boolean | undefined => {
      if (!loadedIds.has(id)) return undefined
      return (childrenByManager.get(id)?.size ?? 0) > 0
    },
    [loadedIds, childrenByManager]
  )

  const ensureExpanded = useCallback((id: string) => {
    setCollapsedIds((prev) => {
      if (!prev.has(id)) return prev
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }, [])

  const toggleExpanded = useCallback(
    (id: string) => {
      if (!loadedIds.has(id)) {
        setPendingExpandIds((prev) => (prev.has(id) ? prev : new Set(prev).add(id)))
        return
      }
      setCollapsedIds((prev) => {
        const next = new Set(prev)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        return next
      })
    },
    [loadedIds]
  )

  /** Loads and expands every ancestor of `employee` so its full reporting
   * line is visible, and returns the ancestor ids (root-first) - used by
   * search-select and focus mode. */
  const focusPathTo = useCallback(async (employee: ChartEmployee): Promise<string[]> => {
    setExtraEmployees((prev) => {
      const next = new Map(prev)
      next.set(employee.id, employee)
      return next
    })
    const ancestors = await fetchReportingLine(employee.id)
    const rootFirst = [...ancestors].reverse()
    setExtraEmployees((prev) => {
      const next = new Map(prev)
      for (const { employee: ancestor } of rootFirst) next.set(ancestor.id, ancestor)
      return next
    })
    setCollapsedIds((prev) => {
      if (rootFirst.every(({ employee: a }) => !prev.has(a.id))) return prev
      const next = new Set(prev)
      for (const { employee: ancestor } of rootFirst) next.delete(ancestor.id)
      return next
    })
    return rootFirst.map(({ employee: ancestor }) => ancestor.id)
  }, [])

  /** Descendant ids of `id` reachable from currently loaded data only (§7.3
   * - drop-target validity is computed client-side from what's loaded; the
   * server's deferred cycle trigger remains the real authority regardless). */
  const getDescendantIds = useCallback(
    (id: string, maxDepth = Infinity): string[] => {
      const result: string[] = []
      const queue: Array<[string, number]> = [[id, 0]]
      while (queue.length > 0) {
        const [current, depth] = queue.shift()!
        if (depth >= maxDepth) continue
        for (const childId of childrenByManager.get(current) ?? []) {
          result.push(childId)
          queue.push([childId, depth + 1])
        }
      }
      return result
    },
    [childrenByManager]
  )

  const invalidateAround = useCallback(
    (ids: (string | null)[]) => {
      const targets = new Set(ids.filter((id): id is string => Boolean(id)))
      const promises = [...targets].map((id) =>
        queryClient.invalidateQueries({ queryKey: employeeKeys.detail(id) })
      )
      promises.push(queryClient.invalidateQueries({ queryKey: hierarchyKeys.roots() }))
      return Promise.all(promises)
    },
    [queryClient]
  )

  const reassignMutation = useMutation({
    mutationFn: async ({
      employeeId,
      newManagerId,
    }: {
      employeeId: string
      newManagerId: string | null
    }) => {
      const employee = employeesById.get(employeeId)
      if (!employee) throw new Error('Unknown employee')
      const { data, error, response } = await apiClient.PUT(
        '/api/v1/employees/{employee_id}/manager',
        {
          params: {
            path: { employee_id: employeeId },
            header: { 'If-Match': `"${employee.version}"` },
          },
          body: { manager_id: newManagerId },
        }
      )
      if (error) {
        if (response.status === 409) {
          throw new ChartVersionConflict(employeeId, 'The record changed since it was last read')
        }
        throw error
      }
      return data
    },
    onMutate: async ({ employeeId, newManagerId }) => {
      const previousManagerId = employeesById.get(employeeId)?.manager_id ?? null
      setManagerOverrides((prev) => new Map(prev).set(employeeId, newManagerId))
      return { previousManagerId }
    },
    onError: (_error, { employeeId }) => {
      setManagerOverrides((prev) => {
        const next = new Map(prev)
        next.delete(employeeId)
        return next
      })
    },
    onSuccess: async (_data, { employeeId, newManagerId }, context) => {
      await invalidateAround([context?.previousManagerId ?? null, newManagerId])
      setManagerOverrides((prev) => {
        const next = new Map(prev)
        next.delete(employeeId)
        return next
      })
    },
  })

  return {
    isLoading,
    isError,
    roots,
    employeesById,
    childrenByManager,
    depthById,
    visibleIds,
    collapsedIds,
    hasChildren,
    toggleExpanded,
    ensureExpanded,
    focusPathTo,
    getDescendantIds,
    reassign: reassignMutation.mutateAsync,
    isReassigning: reassignMutation.isPending,
  }
}

export type OrgChartData = ReturnType<typeof useOrgChartData>
