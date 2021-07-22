/* globals expect, test */
import { renderWithI18n } from '../../i18n/test-utils'
import TimestampCell from './TimestampCell'

test('nanosecond precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34:01.002002002Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34:01.002002002Z')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T18:34:01.002002002Z')
})

test('microsecond precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34:01.002002Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34:01.002002Z')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T18:34:01.002002Z')
})

test('millisecond precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34:01.002Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34:01.002Z')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T18:34:01.002Z')
})

test('second precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34:01Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34:01Z')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T18:34:01Z')
})

test('minute precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18:34Z' />)
  expect(container.textContent).toEqual('2018-08-29T18:34Z')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T18:34Z')
})

test('hour precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T18Z' />)
  expect(container.textContent).toEqual('2018-08-29T18Z')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T18:00Z')
})

test('midnight, compact ISO8601, omit THHZ from text', () => {
  const { container } = renderWithI18n(<TimestampCell value='2021-07-21T00Z' />)
  expect(container.textContent).toEqual('2021-07-21')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2021-07-21T00:00Z')
})

test('midnight, full ISO8601, omit THH...Z from text', () => {
  const { container } = renderWithI18n(<TimestampCell value='2021-07-21T00:00:00.000000Z' />)
  expect(container.textContent).toEqual('2021-07-21')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2021-07-21T00:00:00.000000Z')
})

test('year precision', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T00Z' />)
  expect(container.textContent).toEqual('2018-08-29')
  expect(container.firstChild.getAttribute('datetime')).toEqual('2018-08-29T00:00Z')
})

test('className=cell-timestamp', () => {
  const { container } = renderWithI18n(<TimestampCell value='2018-08-29T00:00:00.000Z' />)
  expect(container.firstChild.className).toEqual('cell-timestamp')
})

test('null => NullCell', () => {
  const { container } = renderWithI18n(<TimestampCell value={null} />)
  expect(container.firstChild.className).toEqual('cell-timestamp cell-null')
})
