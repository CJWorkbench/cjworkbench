import { SparseTileGrid } from './tiles'

function splice (array, index, value) {
  return [...array.slice(0, index), value, ...array.slice(index + 1)]
}

/**
 * Replace an existing tile with a loaded/error tile.
 */
export default function placeTile (sparseTileGrid, tile) {
  const { tileRows } = sparseTileGrid
  const { tileRow, tileColumn } = tile

  const index = tileRows.findIndex(rowOrGap => Array.isArray(rowOrGap) && rowOrGap[0].tileRow === tileRow)
  const newRow = splice(tileRows[index], tileColumn, tile)
  const newTileRows = splice(tileRows, index, newRow)
  return new SparseTileGrid(newTileRows)
}
