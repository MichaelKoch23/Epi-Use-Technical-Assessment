import { formatCurrency, formatDate } from './format'
import type { EmployeesFilterState } from './useEmployeesViewState'

export interface Chip {
  key: string
  label: string
  onRemove: () => void
}

function salaryLabel(min: string, max: string): string {
  if (min && max) return `Salary: ${formatCurrency(min, 'ZAR')} - ${formatCurrency(max, 'ZAR')}`
  if (min) return `Salary: >= ${formatCurrency(min, 'ZAR')}`
  return `Salary: <= ${formatCurrency(max, 'ZAR')}`
}

function birthDateLabel(min: string, max: string): string {
  if (min && max) return `Born: ${formatDate(min)} - ${formatDate(max)}`
  if (min) return `Born: after ${formatDate(min)}`
  return `Born: before ${formatDate(max)}`
}

export function getFilterChips(
  filters: EmployeesFilterState,
  onApply: (patch: Partial<EmployeesFilterState>) => void
): Chip[] {
  const chips: Chip[] = []

  if (filters.position) {
    chips.push({
      key: 'position',
      label: `Position: ${filters.position}`,
      onRemove: () => onApply({ position: '' }),
    })
  }
  if (filters.managerId) {
    chips.push({
      key: 'manager',
      label: `Reports to: ${filters.managerName || filters.managerId}`,
      onRemove: () => onApply({ managerId: '', managerName: '' }),
    })
  }
  if (filters.minSalary || filters.maxSalary) {
    chips.push({
      key: 'salary',
      label: salaryLabel(filters.minSalary, filters.maxSalary),
      onRemove: () => onApply({ minSalary: '', maxSalary: '' }),
    })
  }
  if (filters.minBirthDate || filters.maxBirthDate) {
    chips.push({
      key: 'birth-date',
      label: birthDateLabel(filters.minBirthDate, filters.maxBirthDate),
      onRemove: () => onApply({ minBirthDate: '', maxBirthDate: '' }),
    })
  }

  return chips
}
