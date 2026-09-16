import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AnomalyPanel } from '../components/AnomalyPanel'

const EMPTY_ANOMALIES = {
  wide_spans: [],
  single_report_managers: [],
  deep_chains: [],
  unreachable: [],
}

describe('AnomalyPanel', () => {
  it('renders the "no structural issues" empty state when every group is empty', () => {
    render(
      <MemoryRouter>
        <AnomalyPanel data={EMPTY_ANOMALIES} isPending={false} />
      </MemoryRouter>
    )

    expect(screen.getByText('No structural issues found')).toBeInTheDocument()
  })

  it('renders only the groups that have entries', () => {
    render(
      <MemoryRouter>
        <AnomalyPanel
          data={{
            ...EMPTY_ANOMALIES,
            unreachable: [{ id: 'e1', name: 'Jane Doe', position: 'Engineer' }],
          }}
          isPending={false}
        />
      </MemoryRouter>
    )

    expect(screen.queryByText('No structural issues found')).not.toBeInTheDocument()
    expect(screen.getByText('Unreachable employees')).toBeInTheDocument()
    expect(screen.queryByText('Wide span of control')).not.toBeInTheDocument()
  })
})
