import { z } from 'zod'

// Mirrors app/schemas/fields.py, field for field - the server is the
// authority and re-checks all of this, but a rule enforced only there
// arrives as a 422 toast after a round trip, while the same rule here
// marks the offending input as the user leaves it. Anything added on one
// side belongs on the other; the constants below are the shared contract.
const MAX_SALARY = 9999999999.99 // NUMERIC(12,2)'s ceiling
const MIN_BIRTH_DATE = '1900-01-01'

const requiredText = (label: string, max: number) =>
  z
    .string()
    .trim()
    .min(1, `${label} is required`)
    .max(max, `${label} must be at most ${max} characters`)

// Deliberately the same shape as the server's `_EMAIL_RE`: one @, no
// whitespace, a dot in the domain. Not RFC 5322 - neither side claims to
// be, and a stricter client rule would reject addresses the API accepts.
const email = z
  .string()
  .trim()
  .min(3, 'Email is required')
  .max(320, 'Email must be at most 320 characters')
  .regex(/^[^@\s]+@[^@\s]+\.[^@\s]+$/, 'Must be a valid email address')

const birthDate = z
  .string()
  .trim()
  .min(1, 'Birth date is required')
  .regex(/^\d{4}-\d{2}-\d{2}$/, 'Invalid date')
  .refine((value) => value > MIN_BIRTH_DATE, `Must be after ${MIN_BIRTH_DATE}`)
  .refine(
    (value) => value <= new Date().toISOString().slice(0, 10),
    'Birth date cannot be in the future'
  )

// http(s) only, matching the server's scheme allow-list - `z.string().url()`
// alone also accepts javascript: and data:.
const optionalUrl = z.union([
  z.literal(''),
  z
    .string()
    .trim()
    .max(2048, 'URL must be at most 2048 characters')
    .url('Must be a valid URL')
    .refine(
      (value) => value.startsWith('http://') || value.startsWith('https://'),
      'Must be an http:// or https:// URL'
    ),
])

export const employeeFieldsSchema = z.object({
  employee_number: requiredText('Employee number', 64),
  first_name: requiredText('First name', 100),
  last_name: requiredText('Last name', 100),
  email,
  birth_date: birthDate,
  position: requiredText('Position', 120),
  salary: z.coerce
    .number()
    .min(0, 'Salary must be at least 0')
    .max(MAX_SALARY, 'Salary is too large'),
  currency: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z]{3}$/, 'Currency must be a 3-letter code'),
  avatar_override_url: optionalUrl,
})

export const employeeCreateSchema = employeeFieldsSchema.extend({
  manager_id: z.union([z.literal(''), z.string().uuid()]),
})

export const employeeUpdateSchema = employeeFieldsSchema

// react-hook-form's `useForm` is generic over both the raw (pre-parse) form
// values and the parsed (post-`zodResolver`) output - `salary` coerces a
// string input to a number output, so those two types genuinely differ.
export type EmployeeCreateFormInput = z.input<typeof employeeCreateSchema>
export type EmployeeCreateFormValues = z.infer<typeof employeeCreateSchema>
export type EmployeeUpdateFormInput = z.input<typeof employeeUpdateSchema>
export type EmployeeUpdateFormValues = z.infer<typeof employeeUpdateSchema>
