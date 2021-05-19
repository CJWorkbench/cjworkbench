import React from 'react'
import PropTypes from 'prop-types'
import { columnDefinitionType } from './types'
import {
  FocusCellContext,
  FocusCellSetterContext,
  RowSelectionContext
} from './state'
import RowNumber from './RowNumber'
import Td from './Td'

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

const TBody = React.forwardRef(function TBody (
  { columns, nRows, nSkipRows, nSkipColumns, cells },
  ref
) {
  const rowSelection = React.useContext(RowSelectionContext)
  const focusCell = React.useContext(FocusCellContext)
  const setFocusCell = React.useContext(FocusCellSetterContext)

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
      }
    }
  }, [moveFocus])

  function indexRow (index) {
    return nSkipRows + index
  }

  function indexColumn (index) {
    return nSkipColumns + index
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
              value={value}
              row={indexRow(i)}
              column={indexColumn(j)}
              focus={focusCell && focusCell.row === indexRow(i) && focusCell.column === indexColumn(j)}
              Component={columns[indexColumn(j)].valueComponent}
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
})
TBody.propTypes = {
  columns: PropTypes.arrayOf(columnDefinitionType).isRequired,
  nRows: PropTypes.number.isRequired,
  nSkipRows: PropTypes.number.isRequired,
  nSkipColumns: PropTypes.number.isRequired,
  cells: PropTypes.array.isRequired
}
export default TBody
