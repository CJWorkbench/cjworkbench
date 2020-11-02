import React from 'react'
import PropTypes from 'prop-types'

import TileGap from './TileGap'
import TileRow from './TileRow'
import { tileRowOrGapType, columnDefinitionType } from './types'

/**
 * Organize columns into an Array of one Array[Column] per tile.
 */
function tileColumnDefinitions (columns, nColumnsPerTile) {
  const ret = []
  let tile = []
  ret.push(tile)
  columns.forEach((column, i) => {
    if (i > 0 && i % nColumnsPerTile === 0) {
      tile = []
      ret.push(tile)
    }
    tile.push(column)
  })
  return ret
}

/**
 * Organize tile rows, so we know their metadata.
 */
function tileRowsAndGaps (sparseTileGrid, nRowsPerTile, nRows) {
  const ret = []
  let tileRow = 0
  sparseTileGrid.forEach(tilesOrGap => {
    const rowIndex = tileRow * nRowsPerTile
    if (Number.isInteger(tilesOrGap)) {
      const nRowsInTile = Math.min(tilesOrGap * nRowsPerTile, nRows - rowIndex)
      ret.push({ type: 'gap', rowIndex, nRows: nRowsInTile })
      tileRow += tilesOrGap
    } else {
      const nRowsInTile = Math.min(nRowsPerTile, nRows - rowIndex)
      ret.push({ type: 'tiles', tiles: tilesOrGap, rowIndex, nRows: nRowsInTile })
      tileRow += 1
    }
  })
  return ret
}

function RowNumber ({ index }) { return <>ROW: {index}</> }

export default function BigTable ({
  sparseTileGrid, nRows, columns, nRowsPerTile, nColumnsPerTile, setWantedTileRange
}) {
  const tiledColumnDefinitions = React.useMemo(() => tileColumnDefinitions(columns, nColumnsPerTile), [columns, nColumnsPerTile])
  const tiledColumnComponents = React.useMemo(() => tiledColumnDefinitions.map(x => x.map(y => y.valueComponent)), [tiledColumnDefinitions])
  const tiledRowsAndGaps = React.useMemo(() => tileRowsAndGaps(sparseTileGrid, nRowsPerTile, nRows), [sparseTileGrid, nRowsPerTile, nRows])

  return (
    <table>
      <colgroup>
        <col className='row-number' />
        {tiledColumnDefinitions.map((columnDefinitions, tileColumn) => (
          <React.Fragment key={tileColumn}>
            {columnDefinitions.map(({ width }, i) => (
              <col key={i} style={{ width: `${width}px` /* TODO cache */ }} />
            ))}
          </React.Fragment>
        ))}
      </colgroup>
      <thead>
        <tr>
          <th scope='col' />
          {tiledColumnDefinitions.map((columnDefinitions, tileColumn) => (
            <React.Fragment key={tileColumn}>
              {columnDefinitions.map(({ headerComponent: Header }, i) => (
                <th key={i} scope='col'><Header /></th>
              ))}
            </React.Fragment>
          ))}
        </tr>
      </thead>
      {tiledRowsAndGaps.map(tilesOrGap => (
        tilesOrGap.type === 'tiles' ? (
          <TileRow
            key={tilesOrGap.rowIndex}
            rowNumberComponent={RowNumber}
            tiles={tilesOrGap.tiles}
            rowIndex={tilesOrGap.rowIndex}
            nRows={tilesOrGap.nRows}
            tiledColumnComponents={tiledColumnComponents}
          />
        ) : (
          <TileGap
            key={tilesOrGap.rowIndex}
            nRows={tilesOrGap.nRows}
            nColumns={columns.length}
          />
        )
      ))}
    </table>
  )
}
BigTable.propTypes = {
  sparseTileGrid: PropTypes.arrayOf(tileRowOrGapType.isRequired).isRequired,
  nRows: PropTypes.number.isRequired,
  columns: PropTypes.arrayOf(columnDefinitionType.isRequired).isRequired,
  nRowsPerTile: PropTypes.number.isRequired,
  nColumnsPerTile: PropTypes.number.isRequired,
  setWantedTileRange: PropTypes.func.isRequired // func(r1, r2, c1, c2) => undefined
}
