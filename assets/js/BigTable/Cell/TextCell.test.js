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

test('absolute link => <a>', () => {
  const url = 'http://example.org/page?foo=bar&bar=baz#a23'
  const { container } = renderWithI18n(<TextCell value={url} />)
  expect(container.firstChild.tagName).toEqual('A')
  expect(container.firstChild.className).toEqual('cell-text')
  expect(container.firstChild.href).toEqual(url)
  expect(container.firstChild.textContent).toEqual(url)
})

test('imperfect link => not <a>', () => {
  const url = 'http://example.org/page?foo=bar&bar=baz#a23 '
  const { container } = renderWithI18n(<TextCell value={url} />)
  expect(container.firstChild.tagName).toEqual('DIV')
})

test('percent-encode link paths', () => {
  // https://url.spec.whatwg.org/#example-5434421b
  const { container } = renderWithI18n(<TextCell value='https://example.org/💩' />)
  expect(container.firstChild.href).toEqual('https://example.org/%F0%9F%92%A9')
  expect(container.firstChild.textContent).toEqual('https://example.org/💩')
})

test('punycode link hosts', () => {
  // https://url.spec.whatwg.org/#example-host-psl
  const { container } = renderWithI18n(<TextCell value='http://إختبار' />)
  expect(container.firstChild.href).toEqual('http://xn--kgbechtv/')
  expect(container.firstChild.textContent).toEqual('http://إختبار')
})

test('link with fragment', () => {
  const { container } = renderWithI18n(<TextCell value='https://example.org/page#💩' />)
  expect(container.firstChild.href).toEqual('https://example.org/page#%F0%9F%92%A9')
  expect(container.firstChild.textContent).toEqual('https://example.org/page#💩')
})

test('not link whitespace', () => {
  const { container } = renderWithI18n(<TextCell value='https://example.com ' />)
  expect(container.firstChild.tagName).toEqual('DIV')
})

;
[
  'https:example.org',
  'https://////example.com///',
  'https://user:password@example.org/\t',
  'https://example.org/foo bar',
  'https://ex ample.org/',
  'example',
  'https://example.com:demo',
  'http://[www.example.com]/'
].forEach(url => {
  test(`not link invalid URL ${url}`, () => {
    // as per https://url.spec.whatwg.org/#example-url-parsing
    const { container } = renderWithI18n(<TextCell value={url} />)
    expect(container.firstChild.tagName).toEqual('DIV')
  })
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
