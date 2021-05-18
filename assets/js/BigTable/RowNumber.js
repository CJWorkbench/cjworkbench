import React from 'react'
import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'
import {
  FocusCellContext,
  FocusCellSetterContext,
  RowSelectionContext,
  RowSelectionSetterContext
} from './state'

function handleMouseDown (ev) {
  if (ev.shiftKey) {
    // Don't select table data as text
    ev.preventDefault()
  }
}

export default function RowNumber (props) {
  const focusCell = React.useContext(FocusCellContext)
  const setFocusCell = React.useContext(FocusCellSetterContext)
  const rowSelection = React.useContext(RowSelectionContext)
  const setRowSelection = React.useContext(RowSelectionSetterContext)

  const { rowIndex } = props
  const s = i18n.number(rowIndex + 1)

  const handleClick = React.useCallback(ev => {
    if (rowSelection && setRowSelection) {
      const newSelection = new Uint8Array(Math.max(rowSelection.length, rowIndex + 1))
      newSelection.set(rowSelection)

      if (ev.shiftKey && focusCell && focusCell.column === null && focusCell.row !== null) {
        const checked = rowSelection && rowSelection[(focusCell.row)]
        const [begin, end] = focusCell.row < rowIndex ? [focusCell.row, rowIndex + 1] : [rowIndex, focusCell.row + 1]
        for (let i = begin; i < end; i++) {
          newSelection[i] = checked
        }
      } else {
        const checked = !(rowSelection && rowSelection[rowIndex])
        newSelection[rowIndex] = checked
      }
      setRowSelection(newSelection)
    }

    if (setFocusCell) {
      setFocusCell({ row: rowIndex, column: null })
    }
  }, [rowIndex, focusCell, setFocusCell, rowSelection, setRowSelection])

  return (
    <label data-n-chars={s.length} onMouseDown={handleMouseDown}>
      {rowSelection && setRowSelection
        ? (
          <input
            type='checkbox'
            value={Boolean(rowSelection && rowSelection[rowIndex])}
            onClick={handleClick /* onChange doesn't have ev.shiftKey */}
          />)
        : null}
      {s}
    </label>
  )
}
RowNumber.propTypes = {
  rowIndex: PropTypes.number.isRequired
}
