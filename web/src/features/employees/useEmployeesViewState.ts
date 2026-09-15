import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router'

export const DEFAULT_SORT = 'last_name'
export const DEFAULT_ORDER: 'asc' | 'desc' = 'asc'
export const DEFAULT_PAGE_SIZE = 50

export interface EmployeesFilterState {
  q: string
  position: string
  managerId: string
  /** Not sent to the API — carried in the URL only so the manager chip and
   * the filter popover can show a name without an extra lookup request. */
  managerName: string
  minSalary: string
  maxSalary: string
  minBirthDate: string
  maxBirthDate: string
}

export interface EmployeesViewState extends EmployeesFilterState {
  sort: string
  order: 'asc' | 'desc'
  page: number
  pageSize: number
  deleted: boolean
}

const FILTER_PARAM_KEYS: Record<keyof EmployeesFilterState, string> = {
  q: 'q',
  position: 'position',
  managerId: 'manager_id',
  managerName: 'manager_name',
  minSalary: 'min_salary',
  maxSalary: 'max_salary',
  minBirthDate: 'min_birth_date',
  maxBirthDate: 'max_birth_date',
}

function parseFilters(params: URLSearchParams): EmployeesFilterState {
  return {
    q: params.get('q') ?? '',
    position: params.get('position') ?? '',
    managerId: params.get('manager_id') ?? '',
    managerName: params.get('manager_name') ?? '',
    minSalary: params.get('min_salary') ?? '',
    maxSalary: params.get('max_salary') ?? '',
    minBirthDate: params.get('min_birth_date') ?? '',
    maxBirthDate: params.get('max_birth_date') ?? '',
  }
}

function parsePositiveInt(value: string | null, fallback: number): number {
  const parsed = Number.parseInt(value ?? '', 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

function parseState(params: URLSearchParams): EmployeesViewState {
  return {
    ...parseFilters(params),
    sort: params.get('sort') ?? DEFAULT_SORT,
    order: params.get('order') === 'desc' ? 'desc' : DEFAULT_ORDER,
    page: parsePositiveInt(params.get('page'), 1),
    pageSize: parsePositiveInt(params.get('page_size'), DEFAULT_PAGE_SIZE),
    deleted: params.get('deleted') === 'true',
  }
}

/**
 * Filter/sort/page state lives entirely in the URL (§ shareable views, back
 * button) rather than component state — this hook is the only place that
 * reads or writes it, so the param names are defined once.
 */
export function useEmployeesViewState() {
  const [searchParams, setSearchParams] = useSearchParams()

  // `setSearchParams`'s own functional-updater form hands back a `prev` that
  // can still be one write behind when two of this hook's setters fire in
  // quick succession (e.g. the debounced search commit followed shortly by
  // a sort click) — react-router's internal location hasn't caught up to
  // the just-committed navigation yet, so building off that `prev` silently
  // drops the earlier write. Committing against this ref instead — updated
  // synchronously the moment *we* write, and re-synced from `searchParams`
  // on every render — makes each call build on the last one this hook
  // actually made, not on a snapshot react-router hasn't settled yet.
  const paramsRef = useRef(searchParams)
  useEffect(() => {
    paramsRef.current = searchParams
  }, [searchParams])

  const state = useMemo(() => parseState(searchParams), [searchParams])

  const commit = useCallback(
    (mutate: (next: URLSearchParams) => void) => {
      const next = new URLSearchParams(paramsRef.current)
      mutate(next)
      paramsRef.current = next
      setSearchParams(next, { replace: true })
    },
    [setSearchParams]
  )

  const applyFilters = useCallback(
    (patch: Partial<EmployeesFilterState>) => {
      commit((next) => {
        const merged = { ...parseFilters(next), ...patch }
        for (const key of Object.keys(FILTER_PARAM_KEYS) as (keyof EmployeesFilterState)[]) {
          const value = merged[key]
          const param = FILTER_PARAM_KEYS[key]
          if (value) next.set(param, value)
          else next.delete(param)
        }
        next.delete('page')
      })
    },
    [commit]
  )

  const clearFilters = useCallback(() => {
    commit((next) => {
      for (const param of Object.values(FILTER_PARAM_KEYS)) next.delete(param)
      next.delete('page')
    })
  }, [commit])

  const setSort = useCallback(
    (field: string) => {
      commit((next) => {
        const currentSort = next.get('sort') ?? DEFAULT_SORT
        const currentOrder = next.get('order') === 'desc' ? 'desc' : DEFAULT_ORDER
        const nextOrder = currentSort === field && currentOrder === 'asc' ? 'desc' : 'asc'
        next.set('sort', field)
        next.set('order', nextOrder)
        next.delete('page')
      })
    },
    [commit]
  )

  const setPage = useCallback(
    (page: number) => {
      commit((next) => {
        if (page <= 1) next.delete('page')
        else next.set('page', String(page))
      })
    },
    [commit]
  )

  const setPageSize = useCallback(
    (pageSize: number) => {
      commit((next) => {
        if (pageSize === DEFAULT_PAGE_SIZE) next.delete('page_size')
        else next.set('page_size', String(pageSize))
        next.delete('page')
      })
    },
    [commit]
  )

  const setDeleted = useCallback(
    (deleted: boolean) => {
      commit((next) => {
        if (deleted) next.set('deleted', 'true')
        else next.delete('deleted')
        next.delete('page')
      })
    },
    [commit]
  )

  return { state, applyFilters, clearFilters, setSort, setPage, setPageSize, setDeleted }
}
