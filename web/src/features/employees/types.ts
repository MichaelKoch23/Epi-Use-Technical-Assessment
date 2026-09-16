import type { components } from '@/lib/api-types'

export type EmployeeListItem =
  | components['schemas']['EmployeeListItemRead']
  | components['schemas']['EmployeeListItemReadRestricted']

/** A `viewer` payload omits `salary` entirely (§9.3) rather than nulling
 * it - this is how the client tells the two shapes apart. */
export function hasSalary(
  employee: EmployeeListItem
): employee is components['schemas']['EmployeeListItemRead'] {
  return 'salary' in employee
}
