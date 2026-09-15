import { z } from 'zod'

// Mirrors app/schemas/employee.py's EmployeeCreate/EmployeeUpdate exactly —
// the API itself only enforces "field present" and `salary >= 0`, plus the
// `currency` column's DB-level `CHAR(3)` width, so that's all this
// reproduces (no invented client-only rules the server wouldn't also
// reject), which is what keeps the messages on both sides in sync.
const requiredText = (label: string) => z.string().trim().min(1, `${label} is required`)

const optionalUrl = z.union([z.literal(''), z.string().trim().url('Must be a valid URL')])

export const employeeFieldsSchema = z.object({
  employee_number: requiredText('Employee number'),
  first_name: requiredText('First name'),
  last_name: requiredText('Last name'),
  email: requiredText('Email'),
  birth_date: requiredText('Birth date').regex(/^\d{4}-\d{2}-\d{2}$/, 'Invalid date'),
  position: requiredText('Position'),
  salary: z.coerce.number().min(0, 'Salary must be at least 0'),
  currency: z.string().trim().length(3, 'Currency must be a 3-letter code').toUpperCase(),
  avatar_override_url: optionalUrl,
})

export const employeeCreateSchema = employeeFieldsSchema.extend({
  manager_id: z.union([z.literal(''), z.string().uuid()]),
})

export const employeeUpdateSchema = employeeFieldsSchema

// react-hook-form's `useForm` is generic over both the raw (pre-parse) form
// values and the parsed (post-`zodResolver`) output — `salary` coerces a
// string input to a number output, so those two types genuinely differ.
export type EmployeeCreateFormInput = z.input<typeof employeeCreateSchema>
export type EmployeeCreateFormValues = z.infer<typeof employeeCreateSchema>
export type EmployeeUpdateFormInput = z.input<typeof employeeUpdateSchema>
export type EmployeeUpdateFormValues = z.infer<typeof employeeUpdateSchema>
