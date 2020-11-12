import React from 'react'
import PropTypes from 'prop-types'
import { columnDefinitionType } from './types'
import ColGroup from './ColGroup'
import THead from './THead'
import TBody from './TBody'

export default function Table ({ columns, tbodyRef, nRows, nSkipRows, nSkipColumns, cells }) {
  return (
    <table>
      <ColGroup columns={columns} />
      <THead
        columns={columns}
      />
      <TBody
        ref={tbodyRef}
        columns={columns}
        nRows={nRows}
        nSkipRows={nSkipRows}
        nSkipColumns={nSkipColumns}
        cells={cells}
      />
    </table>
  )
}
Table.propTypes = {
  columns: PropTypes.arrayOf(columnDefinitionType).isRequired,
  tbodyRef: PropTypes.func.isRequired,
  nRows: PropTypes.number.isRequired,
  nSkipRows: PropTypes.number.isRequired,
  nSkipColumns: PropTypes.number.isRequired,
  cells: PropTypes.array.isRequired
}
