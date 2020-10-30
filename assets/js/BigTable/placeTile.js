import { SparseTileGrid } from './tiles'

function splice (array, index, value) {
  return [...array.slice(0, index), value, ...array.slice(index + 1)]
}

function findTileRowIndex(tileRows, tileRow) {
  let tr = 0
  for (let i = 0; i < tileRows.length; i++) {
    const item = tileRows[i]
    if (Number.isInteger(item)) {
      tr += item
    } else {
      if (tr === tileRow) {
        return i
      }
      tr += 1
    }
  }
  throw new Error("Could not find tileRow in tileRows. Is there a gap that should not be there?")
}

/**
 * Replace an existing tile with a loaded/error tile.
 */
export default function placeTile (tileRows, tileRow, tileColumn, tile) {
  const index = findTileRowIndex(tileRows, tileRow)
  const newRow = splice(tileRows[index], tileColumn, tile)
  return splice(tileRows, index, newRow)
}
