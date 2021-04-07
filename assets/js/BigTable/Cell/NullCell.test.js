/* globals expect, test */
import { renderWithI18n } from '../../i18n/test-utils'
import NullCell from './NullCell'

test('have data-text=null', () => {
  const { container } = renderWithI18n(<NullCell type='text' />)
  expect(container.firstChild.getAttribute('data-text')).toEqual('null')
})

test('has textContent="" (for copy+paste))', () => {
  const { container } = renderWithI18n(<NullCell type='text' />)
  expect(container.textContent).toEqual('')
})
