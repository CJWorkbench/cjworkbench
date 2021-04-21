/* globals expect, test */
import { renderWithI18n } from '../../i18n/test-utils'
import { makeNumberCellComponent } from './NumberCell'

test('integer with "{:,}"', () => {
  const Component = makeNumberCellComponent('{:,}')
  const { container } = renderWithI18n(<Component value={1234} />)
  expect(container.textContent).toEqual('1,234')
})

test('className=cell-number', () => {
  const Component = makeNumberCellComponent('{:,}')
  const { container } = renderWithI18n(<Component value={1} />)
  expect(container.firstChild.className).toEqual('cell-number')
})

test('float with "{:,}"', () => {
  const Component = makeNumberCellComponent('{:,}')
  const { container } = renderWithI18n(<Component value={1234.6789} />)
  expect(container.textContent).toEqual('1,234.6789')
})

test('null => NullCell', () => {
  const Component = makeNumberCellComponent('{:,}')
  const { container } = renderWithI18n(<Component value={null} />)
  expect(container.firstChild.className).toEqual('cell-number cell-null')
})

test('0 => not NullCell', () => {
  const Component = makeNumberCellComponent('{:,}')
  const { container } = renderWithI18n(<Component value={0} />)
  expect(container.textContent).toEqual('0')
})

test('prefix and suffix', () => {
  const Component = makeNumberCellComponent('$X{:,.2f}!')
  const { container } = renderWithI18n(<Component value={1234.567} />)
  expect(container.textContent).toEqual('$X1,234.57!')
  expect(container.querySelector('.number-value').textContent).toEqual('1,234.57')
  expect(container.querySelector('.number-prefix').textContent).toEqual('$X')
  expect(container.querySelector('.number-suffix').textContent).toEqual('!')
})

test('percentage with "%" as a suffix', () => {
  const Component = makeNumberCellComponent('{:,.1%}!')
  const { container } = renderWithI18n(<Component value={12.3456} />)
  expect(container.textContent).toEqual('1,234.6%!')
  expect(container.querySelector('.number-suffix').textContent).toEqual('%!')
})

test('invalid format => use default, "{:,}"', () => {
  // Saw this in production on 2019-04-05 -- same day we deployed type
  // formatting for the first time.
  const Component = makeNumberCellComponent('{:nope')
  const { container } = renderWithI18n(<Component value={1234.5678} />)
  expect(container.textContent).toEqual('1,234.5678')
})
