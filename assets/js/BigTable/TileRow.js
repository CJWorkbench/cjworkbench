import React from 'react'
import PropTypes from 'prop-types'

import { tileType } from './types'

function RowInTile ({ tile, rowIndexInTile, nRows, columnComponents }) {
  if (tile === null) {
    return <td className='loading' colSpan={columnComponents.length} />
  } else if (Array.isArray(tile)) {
    return columnComponents.map((ColumnComponent, columnIndex) => (
      <td key={columnIndex}>
        <ColumnComponent value={tile[rowIndexInTile][columnIndex]} />
      </td>
    ))
  } else if ('error' in tile) {
    return rowIndexInTile === 0 ? (
      <td className='error' colSpan={columnComponents.length} rowSpan={nRows}>
        {tile.error.name}: {tile.error.message}
      </td>
    ) : null
  } else {
    throw new Error('Unexpected tile')
  }
}
RowInTile.propTypes = {
  tile: tileType, // null means loading
  rowIndexInTile: PropTypes.number.isRequired,
  nRows: PropTypes.number.isRequired,
  columnComponents: PropTypes.arrayOf(PropTypes.elementType.isRequired).isRequired
}

/**
 * A <tbody> that scans through the given tiles.
 */
export default function TileRow ({ tiles, nRows, tiledColumnComponents, rowNumberComponent, rowIndex }) {
  const RowNumber = rowNumberComponent

  return (
    <tbody>
      {Array(nRows).fill(null).map((_, rowIndexInTile) => (
        <tr key={rowIndexInTile}>
          <th><RowNumber index={rowIndex + rowIndexInTile} /></th>
          {tiles.map((tile, tileIndex) => (
            <RowInTile
              key={tileIndex}
              tile={tile}
              rowIndexInTile={rowIndexInTile}
              nRows={nRows}
              columnComponents={tiledColumnComponents[tileIndex]}
            />
          ))}
        </tr>
      ))}
    </tbody>
  )
}
TileRow.propTypes = {
  tiles: PropTypes.arrayOf(tileType /* null = loading */).isRequired,
  nRows: PropTypes.number.isRequired,
  tiledColumnComponents: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.elementType.isRequired).isRequired).isRequired,
  rowIndex: PropTypes.number.isRequired,
  rowNumberComponent: PropTypes.elementType.isRequired
}
