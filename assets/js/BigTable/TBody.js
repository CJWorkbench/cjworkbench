import React from 'react'
import PropTypes from 'prop-types'
import { columnDefinitionType } from './types'
import RowNumber from './RowNumber'

function SkipRows ({ nRows, nColumns }) {
  const trStyle = React.useMemo(() => ({ height: `calc(${nRows} * var(--row-height)` }), [nRows])
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
      <tr className='updating' key='last'><th /><td colSpan={nColumns} /></tr>
    ]
  } else {
    return <SkipRows nRows={nRows} nColumns={nColumns} />
  }
}

function ValueTd ({ value, valueType, component }) {
  const Component = component
  return <td className={`type-${valueType}`}><Component value={value} /></td>
}

const TBody = React.forwardRef(function TBody ({ columns, nRows, nSkipRows, nSkipColumns, cells }, ref) {
  const nRowsAfter = nRows - nSkipRows - cells.length
  const nColumnsAfter = cells.length === 0 ? null /* never used */ : columns.length - nSkipColumns - cells[0].length

  return (
    <tbody ref={ref}>
      {nSkipRows > 0 ? <SkipRowsAtStart nRows={nSkipRows} nColumns={columns.length} /> : null}
      {cells.map((row, i) => (
        <tr key={nSkipRows + i}>
          <th><RowNumber rowIndex={i + nSkipRows} /></th>
          {nSkipColumns > 0 ? <td className='updating' colSpan={nSkipColumns} /> : null}
          {row.map((value, j) => (
            <ValueTd
              key={j + nSkipColumns}
              valueType={columns[j + nSkipColumns].type}
              value={value}
              component={columns[j + nSkipColumns].valueComponent}
            />
          ))}
          {nColumnsAfter > 0 ? <td className='updating' colSpan={nColumnsAfter} /> : null}
        </tr>
      ))}
      {nRowsAfter > 0 ? <SkipRows nRows={nRowsAfter} nColumns={columns.length} /> : null}
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
