import { columnFilteringFeature, rowPaginationFeature, rowSortingFeature, tableFeatures } from '@tanstack/react-table'
import type { EmployeeListItem } from './types'

export interface EmployeeTableMeta {
  onEdit: (employee: EmployeeListItem) => void
  onDelete: (employee: EmployeeListItem) => void
  onRestore: (employee: EmployeeListItem) => void
  showRestore: boolean
  canEdit: boolean
}

export const employeeTableFeatures = tableFeatures({
  rowSortingFeature,
  columnFilteringFeature,
  rowPaginationFeature,
  tableMeta: {} as EmployeeTableMeta,
})
