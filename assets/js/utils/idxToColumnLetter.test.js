/* globals expect, test */
import idxToColumnLetter from './idxToColumnLetter'

test('0 is A', () => {
  expect(idxToColumnLetter(0)).toBe('A')
})

test('25 is Z', () => {
  expect(idxToColumnLetter(25)).toBe('Z')
})

test('26 is AA', () => {
  expect(idxToColumnLetter(26)).toBe('AA')
})
