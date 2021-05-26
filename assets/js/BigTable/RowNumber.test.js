/* globals expect, jest, test */
import { fireEvent } from '@testing-library/react'
import { renderWithI18n } from '../i18n/test-utils'
import {
  FocusCellContext,
  FocusCellSetterContext,
  RowSelectionContext,
  RowSelectionSetterContext
} from './state'
import RowNumber from './RowNumber'

function render (node) {
  return renderWithI18n(
    <table>
      <tbody>
        <tr>
          {node}
        </tr>
      </tbody>
    </table>
  )
}

function StateProvider (props) {
  const {
    focusCell = undefined,
    setFocusCell = undefined,
    rowSelection = undefined,
    setRowSelection = undefined,
    children
  } = props
  return (
    <FocusCellContext.Provider value={focusCell}>
      <FocusCellSetterContext.Provider value={setFocusCell}>
        <RowSelectionContext.Provider value={rowSelection}>
          <RowSelectionSetterContext.Provider value={setRowSelection}>
            {children}
          </RowSelectionSetterContext.Provider>
        </RowSelectionContext.Provider>
      </FocusCellSetterContext.Provider>
    </FocusCellContext.Provider>
  )
}

test('row 0', () => {
  const { getByText } = render(<RowNumber rowIndex={0} />)
  expect(getByText('1').getAttribute('data-n-chars')).toEqual('1')
})

test('row 1,000 (includes a comma in char count)', () => {
  const { getByText } = render(<RowNumber rowIndex={999} />)
  expect(getByText('1,000').getAttribute('data-n-chars')).toEqual('5')
})

test('set rowSelection from all-deselected (no SHIFT)', () => {
  const setRowSelection = jest.fn()
  const { getByLabelText } = render(
    <StateProvider rowSelection={new Uint8Array()} setRowSelection={setRowSelection}>
      <RowNumber rowIndex={1} />
    </StateProvider>
  )
  fireEvent.click(getByLabelText('2'))
  expect(setRowSelection).toHaveBeenCalledWith(new Uint8Array([0, 1]))
})

test('set rowSelection from all-deselected and no focus (with SHIFT)', () => {
  const setRowSelection = jest.fn()
  const { getByLabelText } = render(
    <StateProvider rowSelection={new Uint8Array()} setRowSelection={setRowSelection}>
      <RowNumber rowIndex={1} />
    </StateProvider>
  )
  fireEvent.click(getByLabelText('2'), { shfitKey: true })
  expect(setRowSelection).toHaveBeenCalledWith(new Uint8Array([0, 1]))
})

test('set rowSelection using SHIFT', () => {
  const setRowSelection = jest.fn()
  const { getByLabelText } = render(
    <StateProvider
      focusCell={{ row: 1, column: null }}
      rowSelection={new Uint8Array([0, 1])}
      setRowSelection={setRowSelection}
    >
      <RowNumber rowIndex={3} />
    </StateProvider>
  )
  fireEvent.click(getByLabelText('4'), { shiftKey: true })
  expect(setRowSelection).toHaveBeenCalledWith(new Uint8Array([0, 1, 1, 1]))
})

test('set rowSelection using SHIFT, from lower to upper', () => {
  const setRowSelection = jest.fn()
  const { getByLabelText } = render(
    <StateProvider
      focusCell={{ row: 8, column: null }}
      rowSelection={new Uint8Array([0, 1, 0, 0, 0, 0, 0, 0, 1, 0])}
      setRowSelection={setRowSelection}
    >
      <RowNumber rowIndex={3} />
    </StateProvider>
  )
  fireEvent.click(getByLabelText('4'), { shiftKey: true })
  expect(setRowSelection).toHaveBeenCalledWith(new Uint8Array([0, 1, 0, 1, 1, 1, 1, 1, 1, 0]))
})
