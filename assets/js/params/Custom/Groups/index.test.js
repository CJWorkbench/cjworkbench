/* globals expect, jest, test */
import Groups from './index'
import { fireEvent } from '@testing-library/react'
import { renderWithI18n } from '../../../i18n/test-utils.js'

const doRender = (extraProps = {}) =>
  renderWithI18n(
    <Groups
      isReadOnly={false}
      name='groups'
      fieldId='groups'
      onChange={jest.fn()}
      applyQuickFix={jest.fn()}
      upstreamValue={extraProps.value || {colnames: [], group_dates: false, date_granularities: {}}}
      {...extraProps}
    />
  )

test('[DEPRECATED] only show dropdown for selected timestamps', () => {
  const { queryByLabelText } = doRender({
    name: 'w',
    value: {
      colnames: ['A'],
      group_dates: true,
      date_granularities: { A: 'H', B: 'H' }
    },
    inputColumns: [
      { name: 'A', type: 'timestamp' },
      { name: 'B', type: 'timestamp' }
    ]
  })

  expect(queryByLabelText('Granularity of “A”')).not.toBe(null)
  expect(queryByLabelText('Granularity of “B”')).toBe(null)
})

test('[DEPRECATED] show current date granularity', () => {
  const { container, getByLabelText } = doRender({
    name: 'w',
    value: {
      colnames: ['A'],
      group_dates: true,
      date_granularities: { A: 'H' }
    },
    inputColumns: [
      { name: 'A', type: 'timestamp' },
      { name: 'B', type: 'text' }
    ]
  })

  expect(getByLabelText('Group dates [deprecated]').checked).toBe(true)
  expect(container.querySelector('select[name="w[date_granularities][A]"]').value).toEqual('H')
})

test('convert from [DEPRECATED] to timestampmath', () => {
  const applyQuickFix = jest.fn()
  const { getByText } = doRender({
    name: 'w',
    value: {
      colnames: ['A', 'B'],
      group_dates: true,
      date_granularities: { A: 'H', B: 'S' }
    },
    inputColumns: [{ name: 'A', type: 'timestamp' }, { name: 'B', type: 'timestamp' }],
    applyQuickFix
  })

  fireEvent.click(getByText('Upgrade to Dates'))
  expect(applyQuickFix).toHaveBeenCalledWith({
    type: 'prependStep',
    moduleSlug: 'timestampmath',
    partialParams: {
      colname1: 'A',
      outcolname: 'A',
      operation: 'startofhour'
    }
  })
  expect(applyQuickFix).toHaveBeenCalledWith({
    type: 'prependStep',
    moduleSlug: 'timestampmath',
    partialParams: {
      colname1: 'B',
      outcolname: 'B',
      operation: 'startofsecond'
    }
  })
})

test('convert from [DEPRECATED] to converttimestamptodate', () => {
  const applyQuickFix = jest.fn()
  const { getByText } = doRender({
    name: 'w',
    value: {
      colnames: ['A', 'B'],
      group_dates: true,
      date_granularities: { A: 'D', B: 'D' }
    },
    inputColumns: [{ name: 'A', type: 'timestamp' }, { name: 'B', type: 'timestamp' }],
    applyQuickFix
  })

  fireEvent.click(getByText('Upgrade to Dates'))
  expect(applyQuickFix).toHaveBeenCalledWith({
    type: 'prependStep',
    moduleSlug: 'converttimestamptodate',
    partialParams: {
      colnames: ['A', 'B'],
      unit: 'day'
    }
  })
})

test('hide deprecated "Group dates" when it is false, so users do not use it', () => {
  const { queryByLabelText } = doRender({
    name: 'w',
    value: {
      colnames: ['A'],
      group_dates: false,
      date_granularities: { A: 'H' }
    },
    inputColumns: [
      { name: 'A', type: 'timestamp' },
      { name: 'B', type: 'text' }
    ]
  })

  expect(queryByLabelText('Group dates [deprecated]')).toBe(null)
})

test('let user check+uncheck "Group dates" without the checkbox disappearing', () => {
  const onChange = jest.fn()
  const { getByLabelText, queryByText } = doRender({
    name: 'w',
    value: {
      colnames: ['A'],
      group_dates: false,
      date_granularities: { A: 'H' }
    },
    upstreamValue: {
      colnames: ['A'],
      group_dates: true,
      date_granularities: { A: 'H' }
    },
    inputColumns: [
      { name: 'A', type: 'timestamp' },
      { name: 'B', type: 'text' }
    ],
    onChange,
  })
  getByLabelText('Group dates [deprecated]')
  expect(queryByText(/Please upgrade/)).toBe(null)
})

test('show timestamp-to-month converter', () => {
  const applyQuickFix = jest.fn()
  const { container, getByText } = doRender({
    name: 'w',
    value: {
      colnames: ['A'],
      group_dates: false,
      date_granularities: {}
    },
    inputColumns: [
      { name: 'A', type: 'timestamp' }
    ],
    applyQuickFix
  })

  expect(container.textContent).toMatch(/“A” holds timestamps/)
  fireEvent.click(getByText('Convert to Date'))
  expect(applyQuickFix).toHaveBeenCalledWith({
    type: 'prependStep',
    moduleSlug: 'converttimestamptodate',
    partialParams: {
      colnames: ['A'],
      unit: 'day'
    }
  })
})

test('show no month-to-day converter', () => {
  const { container } = doRender({
    name: 'w',
    value: {
      colnames: ['A'],
      group_dates: false,
      date_granularities: {}
    },
    inputColumns: [
      { name: 'A', type: 'date', unit: 'month' }
    ]
  })

  expect(container.textContent).toMatch(/“A” holds months/)
  expect(container.querySelector('button')).toBe(null)
})
