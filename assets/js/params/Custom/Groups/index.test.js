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
      {...extraProps}
    />
  )

test('show pseudo-quick-fix when group_dates:true and there are no date columns', () => {
  const applyQuickFix = jest.fn()
  const { getByText } = doRender({
    applyQuickFix,
    name: 'w',
    value: { colnames: [], group_dates: true, date_granularities: {} },
    inputColumns: [{ name: 'A', type: 'text' }]
  })

  fireEvent.click(getByText('Convert columns'))
  expect(applyQuickFix).toHaveBeenCalledWith({
    type: 'prependStep',
    moduleSlug: 'convert-date',
    partialParams: {}
  })
})

test('show message when group_dates:true and there are unselected date columns', () => {
  const { container } = doRender({
    name: 'w',
    value: { colnames: ['A'], group_dates: true, date_granularities: {} },
    inputColumns: [
      { name: 'A', type: 'text' },
      { name: 'B', type: 'timestamp' }
    ]
  })

  expect(container.querySelectorAll('.no-date-selected')).toHaveLength(1)
  expect(container.querySelectorAll('button[name="w[date_granularities][add-module]"]')).toHaveLength(0)
})

test('show dropdown only for selected dates', () => {
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

test('set date granularity when there is no value', () => {
  const onChange = jest.fn()
  const { getByLabelText } = doRender({
    onChange,
    name: 'w',
    value: { colnames: ['A'], group_dates: true, date_granularities: {} },
    inputColumns: [
      { name: 'A', type: 'timestamp' },
      { name: 'B', type: 'text' }
    ]
  })

  fireEvent.change(getByLabelText('Granularity of “A”'), { target: { value: 'H' } })
  expect(onChange).toHaveBeenCalledWith({
    colnames: ['A'],
    group_dates: true,
    date_granularities: { A: 'H' }
  })
})

test('show current date granularity', () => {
  const { container } = doRender({
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

  expect(container.querySelector('select[name="w[date_granularities][A]"]').value).toEqual('H')
})
