/* globals expect, test */
import { renderWithI18n } from '../../i18n/test-utils'
import TimestampCell from './TimestampCell'

test('millisecond precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34:01.002Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34:01.002Z')
})

test('second precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34:01.000Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34:01Z')
})

test('minute precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34:00.000Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34Z')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T18:34:00.000Z')
})

test('year precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T00:00:00.000Z' />)
  expect(container.textContent).toEqual('2018-08-29')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T00:00:00.000Z')
})

test('className=cell-timestamp', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T00:00:00.000Z' />)
  expect(container.firstChild.className).toEqual('cell-timestamp')
})

test('null => NullCell', () => {
  const { container } = renderWithI18n(<TimestampCell value={null} />)
  expect(container.firstChild.className).toEqual('cell-timestamp cell-null')
})
