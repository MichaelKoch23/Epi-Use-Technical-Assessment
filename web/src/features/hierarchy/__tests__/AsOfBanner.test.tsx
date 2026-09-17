import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AsOfBanner } from '../AsOfBanner'
import type { AsOfState } from '../useAsOf'

function state(overrides: Partial<AsOfState>): AsOfState {
  return {
    asOf: '2026-09-17',
    today: '2026-09-17',
    isToday: true,
    isPast: false,
    isFuture: false,
    setAsOf: () => {},
    ...overrides,
  }
}

describe('AsOfBanner', () => {
  it('stays out of the way when viewing today (§26)', () => {
    const { container } = render(<AsOfBanner state={state({})} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('names the date being viewed and says editing is off (§26)', () => {
    render(
      <AsOfBanner
        state={state({ asOf: '2026-06-14', isToday: false, isPast: true })}
      />
    )

    expect(screen.getByRole('status')).toHaveTextContent(
      /Viewing the organisation as at 14 Jun(uary)?.*2026/i
    )
    expect(screen.getByRole('status')).toHaveTextContent(/Editing is disabled/i)
  })

  it('uses the alert token for the past and the teal token for the future (§27)', () => {
    const { rerender } = render(
      <AsOfBanner state={state({ asOf: '2025-06-14', isToday: false, isPast: true })} />
    )
    expect(screen.getByRole('status').className).toContain('status-alert')
    expect(screen.getByRole('status').className).not.toContain('depth-4')
    expect(screen.getByRole('status')).toHaveTextContent(/historical view/i)

    rerender(
      <AsOfBanner state={state({ asOf: '2027-06-14', isToday: false, isFuture: true })} />
    )
    expect(screen.getByRole('status').className).toContain('depth-4')
    expect(screen.getByRole('status').className).not.toContain('status-alert')
    expect(screen.getByRole('status')).toHaveTextContent(/scheduled future view/i)
  })
})
