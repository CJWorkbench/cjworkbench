function createLoadingRow (nTileColumns) {
  return Array(nTileColumns).fill(null)
}

function needsChange (tileRows, tileRowBegin, tileRowEnd) {
  let tileRow = 0 // number
  for (let i = 0; i < tileRows.length; i++) {
    const item = tileRows[i]
    if (Number.isInteger(item)) {
      tileRow += item
      if (tileRow > tileRowBegin) {
        // At least one row was a gap after tileRowBegin
        return true
      }
    } else {
      tileRow += 1
    }
    if (tileRow >= tileRowEnd) {
      // Ignore remaining rows (so our 'tileRow > tileRowBegin' condition won't be triggered)
      break
    }
  }
  return false
}

/**
 * Replace "gaps" with rows of loading tiles, such that [tileRowBegin, tileRowEnd)
 * are rows of tiles.
 *
 * This returns its input when no gaps apply.
 *
 * Assumes the first row is already split.
 */
export default function splitGapsIntoLoadingTiles (tileRows, tileRowBegin, tileRowEnd) {
  if (!needsChange(tileRows, tileRowBegin, tileRowEnd)) {
    // Return input -- so React.useMemo() can help avoid renders
    return tileRows
  }

  if (Number.isInteger(tileRows[0])) {
    throw new Error('First tile-row must not be a gap')
  }

  let tileRow = 0
  const newTileRows = []
  tileRows.forEach(item => {
    if (tileRow >= tileRowEnd) {
      newTileRows.push(item) // pass-through
    } else {
      if (Number.isInteger(item)) {
        if (tileRow + item < tileRowBegin) {
          // Even after adding this number, we haven't reached a critical zone
          // pass-through the number
          tileRow += item
          newTileRows.push(item)
        } else {
          // we'll need to split somewhere
          if (tileRow < tileRowBegin) {
            // there should be a gap at the start, after splitting (though it's smaller)
            newTileRows.push(tileRowBegin - tileRow)
            item -= (tileRowBegin - tileRow)
            tileRow = tileRowBegin
          }
          // For each critical row, split the number into rows
          while (item > 0 && tileRow < tileRowEnd) {
            newTileRows.push(createLoadingRow(tileRows[0].length))
            tileRow++
            item--
          }
          // If there's more to the number, add it to the end
          if (item > 0) {
            tileRow += item
            newTileRows.push(item)
          }
        }
      } else {
        // item is an Array of tiles. Pass it through.
        newTileRows.push(item)
        tileRow += 1
      }
    }
  })

  return newTileRows
}
