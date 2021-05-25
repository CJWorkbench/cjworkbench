import React from 'react'

/** Uint8Array, indexed by row, true meaning "selected". */
const RowSelectionContext = React.createContext()
RowSelectionContext.displayName = 'RowSelectionContext'

/** Function that sets a new RowSelectionContext.value. */
const RowSelectionSetterContext = React.createContext()
RowSelectionSetterContext.displayName = 'RowSelectionSetterContext'

const EmptyRowSelection = new Uint8Array()
function zeroPad (uint8Array, length) {
  if (uint8Array.length === length) {
    return uint8Array
  } else {
    const ret = new Uint8Array(length)
    ret.set(uint8Array)
    return ret
  }
}

function setRowSelectionIfChanged (value, newValue) {
  const length = Math.max(value.length, newValue.length)
  const paddedValue = zeroPad(value, length)
  const paddedNewValue = zeroPad(newValue, length)
  return paddedValue.every((v, i) => v === paddedNewValue[i])
    ? value
    : newValue
}

/**
 * Empower useRowSelection() and useRowSelectionSetter().
 *
 * rowSelection is a Uint8Array indexed by row, 0 (or truncated) for false, 1
 * for true.
 */
export function RowSelectionProvider (props) {
  const [rowSelection, setRowSelection] = React.useReducer(setRowSelectionIfChanged, EmptyRowSelection)

  return (
    <RowSelectionSetterContext.Provider value={setRowSelection}>
      <RowSelectionContext.Provider value={rowSelection}>
        {props.children}
      </RowSelectionContext.Provider>
    </RowSelectionSetterContext.Provider>
  )
}

export function useRowSelection () {
  return React.useContext(RowSelectionContext)
}

export function useRowSelectionSetter () {
  return React.useContext(RowSelectionSetterContext)
}

const FocusCellContext = React.createContext({ row: null, column: null })
FocusCellContext.displayName = 'FocusCellContext'

const FocusCellSetterContext = React.createContext()
FocusCellSetterContext.displayName = 'FocusCellSetterContext'

function setFocusCellIfChanged (value, newValue) {
  return value.row === newValue.row && value.column === newValue.column
    ? value
    : newValue
}

/**
 * Empower useFocusCell() and useFocusCellSetter().
 *
 * focusCell looks like { row: indexOrNone, column: indexOrNone }.
 */
export function FocusCellProvider (props) {
  const [focusCell, setFocusCell] = React.useReducer(setFocusCellIfChanged, { row: null, column: null })

  return (
    <FocusCellSetterContext.Provider value={setFocusCell}>
      <FocusCellContext.Provider value={focusCell}>
        {props.children}
      </FocusCellContext.Provider>
    </FocusCellSetterContext.Provider>
  )
}

export function useFocusCell () {
  return React.useContext(FocusCellContext)
}

export function useFocusCellSetter () {
  return React.useContext(FocusCellSetterContext)
}

export { FocusCellContext, FocusCellSetterContext, RowSelectionContext, RowSelectionSetterContext } // for RowNumber.test.js
