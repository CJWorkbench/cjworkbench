/* global expect, jest, test */
import '../__mocks__/ResizeObserver'
import { renderWithI18n } from '../i18n/test-utils'
import Viewport from './Viewport'

/*
 * Help BigTable/Viewport.js calculate the wanted parts of the table.
 *
 * These are globals! They apply to all tests in this file.
 *
 * <th> -- has x=0, width=60, height=30; also, has a non-null .offsetParent
 * <div> (viewport) -- has width=650, height=200
 *
 * Each non-header cell has width=180. That's a magic number somewhere....
 */
global.HTMLTableCellElement.prototype.getBoundingClientRect = () => (
  { x: 0, width: 60, height: 30 }
)
Object.defineProperty(global.HTMLTableCellElement.prototype, 'offsetParent', { value: 'not null' })
Object.defineProperty(global.HTMLDivElement.prototype, 'clientWidth', { value: 650, writable: true })
Object.defineProperty(global.HTMLDivElement.prototype, 'clientHeight', { value: 1000, writable: true })

function MockHeader (props) {
  return null
}

function MockValue (props) {
  return null
}

test('call setFocusCellRange on render', () => {
  const setFocusCellRange = jest.fn()
  renderWithI18n(
    <Viewport
      nRows={3}
      columns={[{ name: 'ColA', type: 'text', width: 100, headerComponent: MockHeader, valueComponent: MockValue }]}
      nSkipRows={0}
      nSkipColumns={0}
      cells={[['a0'], ['a1'], ['a2']]}
      setFocusCellRange={setFocusCellRange}
    />
  )
  expect(setFocusCellRange).toHaveBeenCalledWith(0, 3, 0, 1)
})

test('never setFocusCellRange with r0=r1, even on zero height', () => {
  // zero height happens when resizing to very small. Showing an iframe
  // or resizing browser dev tools, for instance.
  global.HTMLDivElement.prototype.clientHeight = 0
  const setFocusCellRange = jest.fn()
  renderWithI18n(
    <Viewport
      nRows={3}
      columns={[{ name: 'ColA', type: 'text', width: 100, headerComponent: MockHeader, valueComponent: MockValue }]}
      nSkipRows={0}
      nSkipColumns={0}
      cells={[['a0'], ['a1'], ['a2']]}
      setFocusCellRange={setFocusCellRange}
    />
  )
  expect(setFocusCellRange).toHaveBeenCalledWith(0, 1, 0, 1)
})

test('never setFocusCellRange with c0=c1, even on zero height', () => {
  // not seen in the wild as of 2021-05-26; but tested for parity with the
  // "r0=r1" test which certainly happens in the wild and in dev mode
  global.HTMLDivElement.prototype.clientWidth = 0
  const setFocusCellRange = jest.fn()
  renderWithI18n(
    <Viewport
      nRows={3}
      columns={[
        { name: 'ColA', type: 'text', width: 100, headerComponent: MockHeader, valueComponent: MockValue },
        { name: 'ColB', type: 'text', width: 100, headerComponent: MockHeader, valueComponent: MockValue }
      ]}
      nSkipRows={0}
      nSkipColumns={0}
      cells={[['a0'], ['a1'], ['a2']]}
      setFocusCellRange={setFocusCellRange}
    />
  )
  expect(setFocusCellRange).toHaveBeenCalledWith(0, 1, 0, 1)
})
