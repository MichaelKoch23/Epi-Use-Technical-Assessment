import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router'

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

export function todayIso(): string {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}

export function shiftIso(iso: string, { months = 0, days = 0 }): string {
  const [year, month, day] = iso.split('-').map(Number)
  const lastDayOfTarget = new Date(Date.UTC(year, month + months, 0)).getUTCDate()
  const date = new Date(
    Date.UTC(year, month - 1 + months, Math.min(day, lastDayOfTarget) + days)
  )
  return date.toISOString().slice(0, 10)
}

export interface AsOfState {
  asOf: string
  today: string
  isToday: boolean
  isPast: boolean
  isFuture: boolean
  setAsOf: (next: string | null) => void
}

export function useAsOf(): AsOfState {
  const [searchParams, setSearchParams] = useSearchParams()

  const paramsRef = useRef(searchParams)
  useEffect(() => {
    paramsRef.current = searchParams
  }, [searchParams])

  const today = todayIso()
  const raw = searchParams.get('as_of')
  const asOf = raw && ISO_DATE.test(raw) ? raw : today

  const setAsOf = useCallback(
    (next: string | null) => {
      const params = new URLSearchParams(paramsRef.current)
      if (!next || next === todayIso()) params.delete('as_of')
      else params.set('as_of', next)
      paramsRef.current = params
      setSearchParams(params, { replace: true })
    },
    [setSearchParams]
  )

  return useMemo(
    () => ({
      asOf,
      today,
      isToday: asOf === today,
      isPast: asOf < today,
      isFuture: asOf > today,
      setAsOf,
    }),
    [asOf, today, setAsOf]
  )
}
