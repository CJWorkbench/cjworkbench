import React from 'react'
import PropTypes from 'prop-types'

export default function TileGap ({ nRows, nColumns }) {
  const colSpan = nColumns + 1 // 1 for the row-number <th>
  return <tbody className='gap'><tr><td colSpan={colSpan} rowSpan={nRows} /></tr></tbody>
}
TileGap.propTypes = {
  nRows: PropTypes.number.isRequired,
  nColumns: PropTypes.number.isRequired,
}
