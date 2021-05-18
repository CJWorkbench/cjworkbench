import React from 'react'

/** Uint8Array, indexed by row, true meaning "selected". */
const RowSelectionContext = React.createContext()
RowSelectionContext.displayName = 'RowSelectionContext'

/** Function that sets a new RowSelectionContext.value. */
const RowSelectionSetterContext = React.createContext()
RowSelectionSetterContext.displayName = 'RowSelectionSetterContext'

/** { row, column } indexes */
const FocusCellContext = React.createContext({ row: null, column: null })
FocusCellContext.displayName = 'FocusCellContext'

const FocusCellSetterContext = React.createContext()
FocusCellSetterContext.displayName = 'FocusCellSetterContext'

export {
  FocusCellContext,
  FocusCellSetterContext,
  RowSelectionContext,
  RowSelectionSetterContext
}
