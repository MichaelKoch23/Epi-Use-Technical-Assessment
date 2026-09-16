import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CostPanel } from '../components/CostPanel'

describe('CostPanel', () => {
  it('renders the restricted treatment when cost is absent (§9.3)', () => {
    render(<CostPanel cost={undefined} restricted isPending={false} />)

    expect(screen.getByText(/restricted/i)).toBeInTheDocument()
    expect(screen.queryByText(/total annual/i)).not.toBeInTheDocument()
  })

  it('renders the cost figures for an admin response', () => {
    render(
      <CostPanel
        cost={{ total_annual: '1000000.00', average: '500000.00', median: '480000.00', currency: 'ZAR' }}
        restricted={false}
        isPending={false}
      />
    )

    expect(screen.queryByText(/restricted/i)).not.toBeInTheDocument()
    expect(screen.getByText(/total annual/i)).toBeInTheDocument()
  })
})
