import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { employeeKeys } from '@/lib/queryKeys'
import { useOrgChartData } from '../useOrgChartData'
import type { ChartEmployee } from '../types'

const AS_OF = '2026-09-18'

const ROOT = 'root-1'
const OLD_MANAGER = 'manager-old'
const NEW_MANAGER = 'manager-new'
const MOVER = 'employee-mover'

/** The server's copy of the org, which the mocked endpoints read from. */
let managerOf: Record<string, string | null>
let deleted: Set<string>

function employee(id: string): ChartEmployee {
  return {
    id,
    employee_number: `EMP-${id}`,
    first_name: 'Test',
    last_name: id,
    email: `${id}@example.com`,
    birth_date: '1990-01-01',
    position: 'Tester',
    currency: 'ZAR',
    manager_id: managerOf[id] ?? null,
    avatar_url: '',
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    deleted_at: null,
  } as unknown as ChartEmployee
}

function depthOf(id: string): number {
  let depth = 0
  let cursor = managerOf[id] ?? null
  while (cursor) {
    depth += 1
    cursor = managerOf[cursor] ?? null
  }
  return depth
}

function live(ids: string[]): string[] {
  return ids.filter((id) => !deleted.has(id))
}

type GetOptions = { params?: { path?: { employee_id?: string } } }

vi.mock('@/lib/apiClient', () => ({
  apiClient: {
    GET: vi.fn((path: string, options?: GetOptions) => {
      const id = options?.params?.path?.employee_id ?? ''

      if (path === '/api/v1/hierarchy/roots') {
        return Promise.resolve({ data: { items: [employee(ROOT)] }, error: undefined })
      }
      if (path === '/api/v1/employees/{employee_id}/subtree') {
        // One query loads the whole org, as a root's depth-2 fetch does: the
        // moved employee is cached under the ROOT's key, not either manager's.
        return Promise.resolve({
          data: {
            items: live([ROOT, OLD_MANAGER, NEW_MANAGER, MOVER]).map((each) => ({
              employee: employee(each),
              depth: depthOf(each),
            })),
          },
          error: undefined,
        })
      }
      if (path === '/api/v1/employees/{employee_id}/reporting-line') {
        const ancestors: string[] = []
        let cursor = managerOf[id] ?? null
        while (cursor) {
          ancestors.push(cursor)
          cursor = managerOf[cursor] ?? null
        }
        return Promise.resolve({
          data: { items: ancestors.map((each) => ({ employee: employee(each), depth: 0 })) },
          error: undefined,
        })
      }
      if (path === '/api/v1/employees/{employee_id}') {
        // The API filters soft-deleted rows out of this lookup, so a deleted
        // employee is a 404 rather than a record with deleted_at set.
        if (deleted.has(id)) {
          return Promise.resolve({
            data: undefined,
            error: { detail: 'Employee not found' },
            response: { status: 404 },
          })
        }
        return Promise.resolve({ data: employee(id), error: undefined })
      }
      return Promise.resolve({ data: { items: [] }, error: undefined })
    }),
    PUT: vi.fn((_path: string, options: { body: { manager_id: string | null } }) => {
      managerOf[MOVER] = options.body.manager_id
      return Promise.resolve({
        data: {
          employee: employee(MOVER),
          assignment_id: 'assignment-1',
          effective_from: AS_OF,
          in_force_now: true,
          reason: null,
          cancelled: [],
        },
        error: undefined,
        response: { status: 200 },
      })
    }),
  },
}))

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function withClient(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useOrgChartData', () => {
  beforeEach(() => {
    managerOf = {
      [ROOT]: null,
      [OLD_MANAGER]: ROOT,
      [NEW_MANAGER]: ROOT,
      [MOVER]: OLD_MANAGER,
    }
    deleted = new Set()
  })

  it('shows the employee under the new manager without a reload', async () => {
    const { result } = renderHook(() => useOrgChartData(AS_OF), { wrapper: withClient(makeClient()) })

    await waitFor(() =>
      expect([...(result.current.childrenByManager.get(OLD_MANAGER) ?? [])]).toEqual([MOVER])
    )

    await act(async () => {
      await result.current.reassign({ employeeId: MOVER, newManagerId: NEW_MANAGER })
    })

    await waitFor(() => {
      expect([...(result.current.childrenByManager.get(NEW_MANAGER) ?? [])]).toEqual([MOVER])
      expect([...(result.current.childrenByManager.get(OLD_MANAGER) ?? [])]).toEqual([])
    })
  })

  it('reads back the saved version, so a second move is not a stale If-Match', async () => {
    const { result } = renderHook(() => useOrgChartData(AS_OF), { wrapper: withClient(makeClient()) })

    await waitFor(() => expect(result.current.employeesById.has(MOVER)).toBe(true))

    await act(async () => {
      await result.current.reassign({ employeeId: MOVER, newManagerId: NEW_MANAGER })
    })

    await waitFor(() =>
      expect(result.current.employeesById.get(MOVER)?.manager_id).toBe(NEW_MANAGER)
    )
  })

  it('drops a deleted employee from the chart without a reload', async () => {
    const client = makeClient()
    const { result } = renderHook(() => useOrgChartData(AS_OF), { wrapper: withClient(client) })

    await waitFor(() => expect(result.current.employeesById.has(MOVER)).toBe(true))

    // Reached through search, which pins the record and its ancestors so they
    // render before their subtrees load.
    await act(async () => {
      await result.current.focusPathTo(employee(MOVER))
    })
    expect(result.current.employeesById.has(MOVER)).toBe(true)

    deleted.add(MOVER)
    await act(async () => {
      await client.invalidateQueries({ queryKey: employeeKeys.all })
    })

    await waitFor(() => expect(result.current.employeesById.has(MOVER)).toBe(false))
    expect([...(result.current.childrenByManager.get(OLD_MANAGER) ?? [])]).toEqual([])
  })
})
