/* globals expect, test */
import { renderWithI18n } from '../../i18n/test-utils'
import { makeDateCellComponent } from './DateCell'

test('day', () => {
  const DateCell = makeDateCellComponent('day')
  const { container } = renderWithI18n(<DateCell value='2021-04-07' />)
  expect(container.textContent).toEqual('2021-04-07')
})

test('week', () => {
  const DateCell = makeDateCellComponent('week')
  const { container } = renderWithI18n(<DateCell value='2021-04-05' />)
  expect(container.textContent).toEqual('2021-04-05')
})

test('month', () => {
  const DateCell = makeDateCellComponent('month')
  const { container } = renderWithI18n(<DateCell value='2021-04-01' />)
  expect(container.textContent).toEqual('2021-04')
})

test('quarter', () => {
  const DateCell = makeDateCellComponent('quarter')
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
  const DateCell = makeDateCellComponent('year')
  const { container } = renderWithI18n(<DateCell value='2021-01-01' />)
  expect(container.textContent).toEqual('2021')
})

test('null => NullCell', () => {
  const DateCell = makeDateCellComponent('day')
  const { container } = renderWithI18n(<DateCell value={null} />)
  expect(container.firstChild.className).toEqual('cell-date cell-null')
})
