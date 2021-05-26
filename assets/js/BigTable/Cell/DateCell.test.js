/* globals expect, test */
import { renderWithI18n } from '../../i18n/test-utils'
import { getDateCellComponent } from './DateCell'

test('day', () => {
  const DateCell = getDateCellComponent('day')
  const { container } = renderWithI18n(<DateCell value='2021-04-07' />)
  expect(container.textContent).toEqual('2021-04-07')
})

test('week', () => {
  const DateCell = getDateCellComponent('week')
  const { container } = renderWithI18n(<DateCell value='2021-04-05' />)
  expect(container.textContent).toEqual('2021-04-05')
})

test('month', () => {
  const DateCell = getDateCellComponent('month')
  const { container } = renderWithI18n(<DateCell value='2021-04-01' />)
  expect(container.textContent).toEqual('2021-04')
})

test('quarter', () => {
  const DateCell = getDateCellComponent('quarter')
  let { container } = renderWithI18n(<DateCell value='2021-01-01' />)
  expect(container.textContent).toEqual('2021 Q1')
  container = renderWithI18n(<DateCell value='2021-04-01' />).container
  expect(container.textContent).toEqual('2021 Q2')
  container = renderWithI18n(<DateCell value='2021-07-01' />).container
  expect(container.textContent).toEqual('2021 Q3')
  container = renderWithI18n(<DateCell value='2021-10-01' />).container
  expect(container.textContent).toEqual('2021 Q4')
})

test('year', () => {
  const DateCell = getDateCellComponent('year')
  const { container } = renderWithI18n(<DateCell value='2021-01-01' />)
  expect(container.textContent).toEqual('2021')
})

test('null => NullCell', () => {
  const DateCell = getDateCellComponent('day')
  const { container } = renderWithI18n(<DateCell value={null} />)
  expect(container.firstChild.className).toEqual('cell-date cell-null')
})
