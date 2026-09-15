import { columnFilteringFeature, rowPaginationFeature, rowSortingFeature, tableFeatures } from '@tanstack/react-table'

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
})
