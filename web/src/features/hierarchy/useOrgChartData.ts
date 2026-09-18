import { useCallback, useMemo, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import { analyticsKeys, employeeKeys, hierarchyKeys } from '@/lib/queryKeys'
import type { ChartEmployee } from './types'

const INITIAL_DEPTH = 2
const EXPAND_DEPTH = 1

export async function fetchRoots(asOf: string): Promise<ChartEmployee[]> {
  const { data, error } = await apiClient.GET('/api/v1/hierarchy/roots', {
    params: { query: { as_of: asOf } },
  })
  if (error) throw error
  return data.items
}

export async function fetchSubtree(id: string, asOf: string, depth?: number) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/subtree', {
    params: { path: { employee_id: id }, query: { depth, as_of: asOf } },
  })
  if (error) throw error
  return data.items
}

async function fetchEmployee(id: string): Promise<ChartEmployee> {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}', {
    params: { path: { employee_id: id } },
  })
  if (error) throw error
  return data
}

async function fetchReportingLine(id: string, asOf: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/reporting-line', {
    params: { path: { employee_id: id }, query: { as_of: asOf } },
  })
  if (error) throw error
  return data.items
}

export class ChartVersionConflict extends Error {
  employeeId: string
  constructor(employeeId: string, message: string) {
    super(message)
    this.name = 'ChartVersionConflict'
    this.employeeId = employeeId
  }
}

export function useOrgChartData(asOf: string) {
  const queryClient = useQueryClient()

  const rootsQuery = useQuery({
    queryKey: hierarchyKeys.roots(asOf),
    queryFn: () => fetchRoots(asOf),
  })
  const roots = useMemo(() => rootsQuery.data ?? [], [rootsQuery.data])

  const rootSubtrees = useQueries({
    queries: roots.map((root) => ({
      queryKey: employeeKeys.subtree(root.id, asOf, INITIAL_DEPTH),
      queryFn: () => fetchSubtree(root.id, asOf, INITIAL_DEPTH),
    })),
  })

  const [pendingExpandIds, setPendingExpandIds] = useState<Set<string>>(new Set())
  const expandQueries = useQueries({
    queries: [...pendingExpandIds].map((id) => ({
      queryKey: employeeKeys.subtree(id, asOf, EXPAND_DEPTH),
      queryFn: () => fetchSubtree(id, asOf, EXPAND_DEPTH),
    })),
  })

  /**
   * People pinned into the chart by a search or a ?focus= link, who may sit
   * outside every loaded subtree. They are held as queries rather than as a
   * frozen copy so that a delete or an edit elsewhere reaches them: a snapshot
   * would keep drawing someone the server has already removed until a reload.
   */
  const [extraIds, setExtraIds] = useState<Set<string>>(new Set())
  const extraQueries = useQueries({
    queries: [...extraIds].map((id) => ({
      queryKey: employeeKeys.detail(id),
      queryFn: () => fetchEmployee(id),
      // A deleted employee is a 404 here, which is an answer, not a failure.
      retry: false,
    })),
  })

  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set())

  const [managerOverrides, setManagerOverrides] = useState<Map<string, string | null>>(new Map())

  const isLoading = rootsQuery.isLoading || rootSubtrees.some((q) => q.isLoading)
  const isError = rootsQuery.isError || rootSubtrees.some((q) => q.isError)

  const rootSubtreesVersion = rootSubtrees.map((q) => `${q.dataUpdatedAt}:${q.status}`).join('|')
  const expandQueriesVersion = expandQueries.map((q) => `${q.dataUpdatedAt}:${q.status}`).join('|')
  const extraQueriesVersion = extraQueries.map((q) => `${q.dataUpdatedAt}:${q.status}`).join('|')

  const { employeesById, childrenByManager, loadedIds } = useMemo(() => {
    const employeesById = new Map<string, ChartEmployee>()
    const childrenByManager = new Map<string, Set<string>>()
    const loadedIds = new Set<string>()

    for (const query of extraQueries) {
      if (query.isError || !query.data) continue
      employeesById.set(query.data.id, query.data)
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    roots,
    rootSubtreesVersion,
    pendingExpandIds,
    expandQueriesVersion,
    extraIds,
    extraQueriesVersion,
    managerOverrides,
  ])

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

  /**
   * The branches whose children are still in flight. Expanding a deep node can
   * take a moment, and without this the chevron looks like it did nothing.
   */
  const expandingIds = useMemo(() => {
    const ids = new Set<string>()
    ;[...pendingExpandIds].forEach((id, index) => {
      if (expandQueries[index]?.isLoading) ids.add(id)
    })
    return ids
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingExpandIds, expandQueriesVersion])

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

  const focusPathTo = useCallback(async (employee: ChartEmployee): Promise<string[]> => {
    // Seeded into the cache so the node draws immediately, then tracked as a
    // query so later invalidations refresh - or retire - it.
    const pin = (record: ChartEmployee) =>
      queryClient.setQueryData(employeeKeys.detail(record.id), record)

    pin(employee)
    setExtraIds((prev) => (prev.has(employee.id) ? prev : new Set(prev).add(employee.id)))

    const ancestors = await fetchReportingLine(employee.id, asOf)
    const rootFirst = [...ancestors].reverse()
    for (const { employee: ancestor } of rootFirst) pin(ancestor)
    setExtraIds((prev) => {
      const next = new Set(prev)
      for (const { employee: ancestor } of rootFirst) next.add(ancestor.id)
      return next.size === prev.size ? prev : next
    })
    setCollapsedIds((prev) => {
      if (rootFirst.every(({ employee: a }) => !prev.has(a.id))) return prev
      const next = new Set(prev)
      for (const { employee: ancestor } of rootFirst) next.delete(ancestor.id)
      return next
    })
    return rootFirst.map(({ employee: ancestor }) => ancestor.id)
  }, [asOf, queryClient])

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

  /**
   * A move changes a row that is cached under whichever node's subtree query
   * fetched it - a root, or whichever ancestor was expanded - and not under
   * either manager's own key. Invalidating just the two managers therefore
   * leaves the moved employee's stale manager_id (and stale version, which the
   * next If-Match is built from) in the cache, so the node springs back to its
   * old parent the moment the optimistic override is dropped.
   */
  const invalidateChartData = useCallback(
    () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: employeeKeys.all }),
        queryClient.invalidateQueries({ queryKey: hierarchyKeys.all }),
        queryClient.invalidateQueries({ queryKey: analyticsKeys.all }),
      ]),
    [queryClient]
  )

  const reassignMutation = useMutation({
    mutationFn: async ({
      employeeId,
      newManagerId,
      effectiveFrom,
      reason,
    }: {
      employeeId: string
      newManagerId: string | null
      effectiveFrom?: string
      reason?: string
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
          body: {
            manager_id: newManagerId,
            effective_from: effectiveFrom ?? null,
            reason: reason ?? null,
          },
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
    onMutate: ({ employeeId, newManagerId, effectiveFrom }) => {
      if (!effectiveFrom || effectiveFrom <= asOf) {
        setManagerOverrides((prev) => new Map(prev).set(employeeId, newManagerId))
      }
    },
    onError: (_error, { employeeId }) => {
      setManagerOverrides((prev) => {
        const next = new Map(prev)
        next.delete(employeeId)
        return next
      })
    },
    onSuccess: async (data, { employeeId }) => {
      // The response carries the saved row, so a node held here from a search
      // does not keep answering with the reporting line it was moved off.
      if (data?.employee) {
        queryClient.setQueryData(employeeKeys.detail(employeeId), data.employee)
      }
      await invalidateChartData()
      void queryClient.invalidateQueries({ queryKey: hierarchyKeys.scheduled() })
      void queryClient.invalidateQueries({
        queryKey: employeeKeys.assignmentHistory(employeeId),
      })
      // Dropped only once the refetch has landed, so the move never flickers
      // back to the old parent in between.
      setManagerOverrides((prev) => {
        const next = new Map(prev)
        next.delete(employeeId)
        return next
      })
      return data
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
    expandingIds,
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
