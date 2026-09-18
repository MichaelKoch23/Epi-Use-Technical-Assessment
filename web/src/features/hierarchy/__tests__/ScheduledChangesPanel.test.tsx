import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ScheduledChangesPanel } from '../ScheduledChangesPanel'
import type { AsOfState } from '../useAsOf'

const cancelScheduled = vi.fn()

vi.mock('../api', () => ({
  fetchScheduled: () =>
    Promise.resolve([
      {
        id: 'assignment-1',
        employee_id: 'employee-1',
        employee_name: 'Nadia Govender',
        employee_position: 'Finance Manager',
        manager_id: 'manager-1',
        manager_name: 'Zanele Smith',
        effective_from: '2026-11-04',
        reason: 'Promotion',
        created_by_email: 'seed@employee.example.com',
      },
    ]),
  cancelScheduled: (id: string) => cancelScheduled(id),
}))

const asOfState: AsOfState = {
  asOf: '2026-09-18',
  today: '2026-09-18',
  isToday: true,
  isPast: false,
  isFuture: false,
  setAsOf: () => {},
}

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ScheduledChangesPanel state={asOfState} canEdit />
    </QueryClientProvider>
  )
}

describe('ScheduledChangesPanel', () => {
  beforeEach(() => {
    cancelScheduled.mockReset()
    cancelScheduled.mockResolvedValue(undefined)
  })

  it('asks before cancelling, instead of cancelling on the first click', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }))

    expect(await screen.findByRole('alertdialog')).toHaveTextContent(
      /Cancel this scheduled move\?/i
    )
    expect(cancelScheduled).not.toHaveBeenCalled()
  })

  it('names the move in the confirmation so it cannot be mistaken for another row', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }))
    const dialog = await screen.findByRole('alertdialog')

    expect(dialog).toHaveTextContent(/Nadia Govender/)
    expect(dialog).toHaveTextContent(/Zanele Smith/)
  })

  it('only cancels once the confirmation is accepted', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }))
    fireEvent.click(await screen.findByRole('button', { name: /cancel the move/i }))

    await waitFor(() => expect(cancelScheduled).toHaveBeenCalledWith('assignment-1'))
  })

  it('keeps the move when the dialog is dismissed', async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }))
    fireEvent.click(await screen.findByRole('button', { name: /keep it scheduled/i }))

    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument())
    expect(cancelScheduled).not.toHaveBeenCalled()
  })
})
