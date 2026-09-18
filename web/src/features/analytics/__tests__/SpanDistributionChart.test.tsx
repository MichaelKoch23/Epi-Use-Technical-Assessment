import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SpanDistributionChart } from '../components/SpanDistributionChart'

describe('SpanDistributionChart', () => {
  it('gives bars outside the healthy range (3-10) the alert token', () => {
    render(
      <SpanDistributionChart
        data={[
          { direct_reports: 5, manager_count: 8 },
          { direct_reports: 15, manager_count: 2 },
        ]}
        isPending={false}
      />
    )

    expect(screen.getByTestId('span-bar-fill-5')).toHaveClass('bg-brand-steel')
    expect(screen.getByTestId('span-bar-fill-15')).toHaveClass('bg-status-alert')
  })
})
