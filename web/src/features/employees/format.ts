export function formatCurrency(amount: number | string, currency: string): string {
  const value = typeof amount === 'string' ? Number(amount) : amount
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-ZA', { dateStyle: 'medium' }).format(new Date(iso))
}
