/* globals expect, test */
import { renderWithI18n } from '../../i18n/test-utils'
import TextCell from './TextCell'

test('text', () => {
  const { container } = renderWithI18n(<TextCell value='hi' />)
  expect(container.textContent).toEqual('hi')
})

test('null => NullCell', () => {
  const { container } = renderWithI18n(<TextCell value={null} />)
  expect(container.firstChild.className).toEqual('cell-text cell-null')
})

test('empty string => not NullCell', () => {
  const { container } = renderWithI18n(<TextCell value='' />)
  expect(container.firstChild.className).toEqual('cell-text')
  expect(container.textContent).toEqual('')
})

test('className=cell-text', () => {
  const { container } = renderWithI18n(<TextCell value='hi' />)
  expect(container.firstChild.className).toEqual('cell-text')
})

test('show whitespace as special characters', () => {
  // relates to https://www.pivotaltracker.com/story/show/159269958
  // We use CSS to preserve whitespace, and we use 'pre' because we
  // don't want to wrap. But we also don't want to try and fit
  // multiple lines of text into one line; and we want CSS's ellipsize
  // code to work.
  //
  // So here it is:
  // whitespace: pre -- preserves whitespace, never wraps
  // text-overflow: ellipsis -- handles single line too long
  // adding ellipsis (what we're testing here) -- handles multiple lines
  const text = '  Veni \r\r\n\n\u2029 Vi\t\vdi  \f  Vici'
  const { container } = renderWithI18n(<TextCell value={text} />)
  expect(container.textContent).toEqual('  Veni ↵↵↵¶ Vi\t⭿di  ↡  Vici')
  expect(container.firstChild.getAttribute('title')).toEqual(text) // for when user hovers
})
