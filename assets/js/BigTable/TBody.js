import React from 'react'
import PropTypes from 'prop-types'
import { columnDefinitionType } from './types'
import { useFocusCell, useFocusCellSetter, useRowSelection } from './state'
import RowNumber from './RowNumber'
import Td from './Td'
import TextCell from './Cell/TextCell'

function SkipRows ({ nRows, nColumns }) {
  const trStyle = React.useMemo(
    () => ({ height: `calc(${nRows} * var(--row-height)` }),
    [nRows]
  )
  return (
    <tr className='updating' data-n-rows={nRows} style={trStyle}>
      <th />
      <td colSpan={nColumns} />
    </tr>
  )
}

/**
 * Render a td with rowspan=nRows, so lower rows are positioned correctly
 *
 * If nRows is even, an even number of rows is returned (so CSS styling with
 * `tr:nth-child(2n + 1)` works as expected -- as it's a common case).
 */
function SkipRowsAtStart ({ nRows, nColumns }) {
  if (nRows % 2 === 0) {
    return [
      <SkipRows key='rest' nRows={nRows - 1} nColumns={nColumns} />,
      <tr className='updating' key='last'>
        <th />
        <td colSpan={nColumns} />
      </tr>
    ]
  } else {
    return <SkipRows nRows={nRows} nColumns={nColumns} />
  }
}

const TBody = React.memo(React.forwardRef(function TBody (props, ref) {
  const { columns, nRows, nSkipRows, nSkipColumns, cells, onEdit } = props
  const [editing, setEditing] = React.useState(null) // { row, column, value, submitting }
  const rowSelection = useRowSelection()
  const focusCell = useFocusCell()
  const setFocusCell = useFocusCellSetter()

  const nRowsAfter = nRows - nSkipRows - cells.length
  const nColumnsAfter =
    cells.length === 0
      ? null /* never used */
      : columns.length - nSkipColumns - cells[0].length

  const moveFocus = React.useMemo(() => {
    if (!setFocusCell || !focusCell) return undefined
    return (ev, dRow, dColumn) => {
      let { row, column } = focusCell
      if (dRow !== null) {
        if (row === null) {
          row = 0
        } else {
          row = Math.max(0, Math.min(nRows - 1, row + dRow))
        }
      }
      if (dColumn !== null) {
        if (column === null) {
          column = 0
        } else {
          column = Math.max(0, Math.min(columns.length - 1, column + dColumn))
        }
      }
      ev.preventDefault() // don't browser-scroll. Instead, scroll when focusCell changes
      setFocusCell({ row, column })
    }
  }, [nRows, columns.length, focusCell, setFocusCell])

  const maybeEnterEditMode = React.useMemo(() => {
    if (!focusCell || focusCell.row === null || focusCell.column === null || editing) return undefined

    return () => {
      const i = focusCell.row - nSkipRows
      const j = focusCell.column - nSkipColumns

      if (i >= 0 && i < cells.length && j >= 0 && j < cells[i].length) {
        const value = cells[i][j]
        setEditing({
          row: focusCell.row,
          column: focusCell.column,
          value: value === null ? '' : String(value),
          submitting: false
        })
      }
    }
  }, [editing, focusCell, cells, nSkipRows, nSkipColumns])

  const handleKeyDown = React.useMemo(() => {
    if (!moveFocus) return undefined
    return ev => {
      switch (ev.key) {
        case 'ArrowDown': return moveFocus(ev, 1, null)
        case 'ArrowLeft': return moveFocus(ev, null, -1)
        case 'ArrowRight': return moveFocus(ev, null, 1)
        case 'ArrowUp': return moveFocus(ev, -1, null)
        case 'PageDown': return moveFocus(ev, 20, null)
        case 'PageUp': return moveFocus(ev, -20, null)
        case 'Enter': return maybeEnterEditMode ? maybeEnterEditMode() : undefined
      }
    }
  }, [maybeEnterEditMode, moveFocus])

  const handleDoubleClickTd = React.useMemo(() => {
    if (!maybeEnterEditMode) return undefined

    return ev => {
      if (ev.button === 0) {
        maybeEnterEditMode() // double-click always fires on focused cell
      }
    }
  }, [maybeEnterEditMode])

  const handleChangeEdit = React.useCallback(ev => {
    if (!editing.submitting) {
      const { row, column } = editing
      setEditing({ row, column, value: ev.target.value, submitting: false })
    }
  }, [editing, setEditing])

  const handleSubmitEdit = React.useCallback(({ oldValue, newValue }) => {
    if (!editing) return // e.g., we just called onCancel()
    const { row, column } = editing
    setEditing({ row, column, value: newValue, submitting: true })
    onEdit({ row, column, oldValue, newValue })
  }, [editing, setEditing, columns, onEdit])

  const handleCancelEdit = React.useCallback(() => {
    if (editing && !editing.submitting) {
      setEditing(null)
    }
  }, [editing, setEditing])

  function indexRow (index) {
    return nSkipRows + index
  }

  function indexColumn (index) {
    return nSkipColumns + index
  }

  function isEditing (i, j) {
    return editing && i === indexRow(editing.row) && j === indexColumn(editing.column) && !editing.submitting
  }

  function isSubmitting (i, j) {
    return editing && i === indexRow(editing.row) && j === indexColumn(editing.column) && editing.submitting
  }

  return (
    <tbody tabIndex='0' onKeyDown={handleKeyDown} ref={ref}>
      {nSkipRows > 0
        ? <SkipRowsAtStart nRows={nSkipRows} nColumns={columns.length} />
        : null}
      {cells.map((row, i) => (
        <tr key={indexRow(i)} className={rowSelection && rowSelection[indexRow(i)] ? 'selected' : undefined}>
          <RowNumber rowIndex={indexRow(i)} />
          {nSkipColumns > 0
            ? <td className='updating' colSpan={nSkipColumns} />
            : null}
          {row.map((value, j) => (
            <Td
              key={indexColumn(j)}
              valueType={columns[indexColumn(j)].type}
              value={isSubmitting(i, j) ? editing.value : value}
              editValue={isEditing(i, j) ? editing.value : null}
              row={indexRow(i)}
              column={indexColumn(j)}
              focus={focusCell && focusCell.row === indexRow(i) && focusCell.column === indexColumn(j)}
              onChange={handleChangeEdit}
              onSubmit={handleSubmitEdit}
              onCancel={handleCancelEdit}
              onDoubleClick={handleDoubleClickTd}
              Component={isSubmitting(i, j) ? TextCell : columns[indexColumn(j)].valueComponent}
            />
          ))}
          {nColumnsAfter > 0
            ? <td className='updating' colSpan={nColumnsAfter} />
            : null}
        </tr>
      ))}
      {nRowsAfter > 0
        ? <SkipRows nRows={nRowsAfter} nColumns={columns.length} />
        : null}
    </tbody>
  )
}))
TBody.propTypes = {
  columns: PropTypes.arrayOf(columnDefinitionType).isRequired,
  nRows: PropTypes.number.isRequired,
  nSkipRows: PropTypes.number.isRequired,
  nSkipColumns: PropTypes.number.isRequired,
  cells: PropTypes.array.isRequired,
  onEdit: PropTypes.func // func({ row, column, oldValue, newValue }) => undefined, or null
}
export default TBody
