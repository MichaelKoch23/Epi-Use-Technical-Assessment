import type { components } from '@/lib/api-types'

export type EmployeeListItem =
  | components['schemas']['EmployeeListItemRead']
  | components['schemas']['EmployeeListItemReadRestricted']

export function hasSalary(
  employee: EmployeeListItem
): employee is components['schemas']['EmployeeListItemRead'] {
  return 'salary' in employee
}
