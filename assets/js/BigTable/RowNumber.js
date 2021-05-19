import React from 'react'
import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'
import { useFocusCell, useFocusCellSetter, useRowSelection, useRowSelectionSetter } from './state'

function handleMouseDown (ev) {
  if (ev.button === 0 && ev.shiftKey) {
    // Don't select table data as text
    ev.preventDefault()
  }
}

const RowNumber = React.memo(function RowNumber (props) {
  const focusCell = useFocusCell()
  const setFocusCell = useFocusCellSetter()
  const rowSelection = useRowSelection()
  const setRowSelection = useRowSelectionSetter()

  const { rowIndex } = props
  const s = i18n.number(rowIndex + 1)

  const handleClick = React.useCallback(ev => {
    if (rowSelection && setRowSelection) {
      const newSelection = new Uint8Array(Math.max(rowSelection.length, rowIndex + 1))
      newSelection.set(rowSelection)

      const checked = !(rowSelection && rowSelection[rowIndex])
      if (ev.shiftKey && focusCell && focusCell.column === null && focusCell.row !== null) {
        const [begin, end] = focusCell.row < rowIndex ? [focusCell.row, rowIndex + 1] : [rowIndex, focusCell.row + 1]
        for (let i = begin; i < end; i++) {
          newSelection[i] = checked
        }
      } else {
        newSelection[rowIndex] = checked
      }
      setRowSelection(newSelection)
    }

    if (setFocusCell) {
      setFocusCell({ row: rowIndex, column: null })
    }
  }, [rowIndex, focusCell, setFocusCell, rowSelection, setRowSelection])

  return (
    <th className={focusCell && focusCell.column === null && focusCell.row === rowIndex ? 'focus' : undefined}>
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
    </th>
  )
})
RowNumber.propTypes = {
  rowIndex: PropTypes.number.isRequired
}
export default RowNumber
