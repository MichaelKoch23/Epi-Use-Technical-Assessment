import { columnFilteringFeature, rowPaginationFeature, rowSortingFeature, tableFeatures } from '@tanstack/react-table'
import type { EmployeeListItem } from './types'

/** Row-action callbacks the "actions" column needs, injected via
 * `useTable({ meta })` instead of threading props through every column
 * definition (§table-state: `table.options.meta`). */
export interface EmployeeTableMeta {
  onEdit: (employee: EmployeeListItem) => void
  onDelete: (employee: EmployeeListItem) => void
  onRestore: (employee: EmployeeListItem) => void
  showRestore: boolean
}

/**
 * Sorting, filtering and pagination are all owned by the server (fully
 * manual mode — see EmployeesListPage), so only the feature/state slots are
 * registered here, with no row-model factories: nothing ever processes rows
 * locally, and `manualSorting`/`manualFiltering`/`manualPagination` each
 * only type-check once their feature is registered (TanStack Table v9).
 */
export const employeeTableFeatures = tableFeatures({
  rowSortingFeature,
  columnFilteringFeature,
  rowPaginationFeature,
  tableMeta: {} as EmployeeTableMeta,
})
