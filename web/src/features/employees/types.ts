import type { components } from '@/lib/api-types'

export type EmployeeListItem =
  | components['schemas']['EmployeeListItemRead']
  | components['schemas']['EmployeeListItemReadRestricted']

export function hasSalary(
  employee: EmployeeListItem
): employee is components['schemas']['EmployeeListItemRead'] {
  return 'salary' in employee
}

/**
 * The shape the manager picker needs to render a choice. Both the search
 * results and the filtered-manager suggestions satisfy it structurally, so the
 * picker does not care which it was handed.
 */
export type ManagerOption = components['schemas']['ManagerOptionRead']
