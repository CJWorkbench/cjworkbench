function copy2DArrayData (fromArray, toArray, fromRowBegin, fromColumnBegin, toRowBegin, toColumnBegin, nRows, nColumns) {
  for (let i = 0; i < nRows; i++) {
    for (let j = 0; j < nColumns; j++) {
      toArray[toRowBegin + i][toColumnBegin + j] = fromArray[fromRowBegin + i][fromColumnBegin + j]
    }
  }
}

function copyTileRow (tileRow, cells, nColumnsPerTile, fromRowBegin, fromColumnBegin, toRowBegin, nRows, nColumns) {
  const tileIndexBegin = Math.floor(fromColumnBegin / nColumnsPerTile)
  const tileIndexEnd = Math.ceil((fromColumnBegin + nColumns) / nColumnsPerTile)
  const firstTileOffsetFromStart = fromColumnBegin % nColumnsPerTile
  const lastTileOffsetFromEnd = tileIndexEnd * nColumnsPerTile - (fromColumnBegin + nColumns)

  for (let i = tileIndexBegin; i < tileIndexEnd; i++) {
    const tile = tileRow[i]
    if (!Array.isArray(tile)) {
      continue // This tile isn't loaded. Leave `cells` all-null, which we assume they are already
    }

    const fromTileColumnBegin = i === tileIndexBegin ? firstTileOffsetFromStart : 0
    const toCellsColumnBegin = i === tileIndexBegin
      ? 0
      : (i - tileIndexBegin) * nColumnsPerTile - firstTileOffsetFromStart
    const nColumnsInTile = (
      nColumnsPerTile -
      (i === tileIndexBegin ? firstTileOffsetFromStart : 0) -
      (i === tileIndexEnd - 1 ? lastTileOffsetFromEnd : 0)
    )

    copy2DArrayData(
      tile,
      cells,
      fromRowBegin,
      fromTileColumnBegin,
      toRowBegin,
      toCellsColumnBegin,
      nRows,
      nColumnsInTile
    )
  }
}

export default function getCellRange (sparseTileGrid, nRowsPerTile, nColumnsPerTile, rowBegin, rowEnd, columnBegin, columnEnd) {
  const cells = new Array(rowEnd - rowBegin).fill(null).map(() => new Array(columnEnd - columnBegin).fill(null))

  const tileRowIndexBegin = Math.floor(rowBegin / nRowsPerTile)
  const tileRowIndexEnd = Math.ceil(rowEnd / nRowsPerTile)
  const firstTileRowOffsetFromStart = rowBegin % nRowsPerTile
  const lastTileRowOffsetFromEnd = tileRowIndexEnd * nRowsPerTile - rowEnd

  let tileRowIndex = 0
  for (let i = 0; i < sparseTileGrid.length && tileRowIndex < tileRowIndexEnd; i++) {
    const tileRowOrGap = sparseTileGrid[i]
    if (Number.isInteger(tileRowOrGap)) {
      const gap = tileRowOrGap
      tileRowIndex += gap
    } else {
      if (tileRowIndex >= tileRowIndexBegin) {
        const tileRow = tileRowOrGap
        const fromTileRowBegin = tileRowIndex === tileRowIndexBegin ? firstTileRowOffsetFromStart : 0
        const toCellsRowBegin = tileRowIndex === tileRowIndexBegin
          ? 0
          : (tileRowIndex - tileRowIndexBegin) * nRowsPerTile - firstTileRowOffsetFromStart
        const nRowsInTileRow = (
          nRowsPerTile -
          (tileRowIndex === tileRowIndexBegin ? firstTileRowOffsetFromStart : 0) -
          (tileRowIndex === tileRowIndexEnd - 1 ? lastTileRowOffsetFromEnd : 0)
        )

        copyTileRow(
          tileRow,
          cells,
          nColumnsPerTile,
          fromTileRowBegin,
          columnBegin,
          toCellsRowBegin,
          nRowsInTileRow,
          columnEnd - columnBegin
        )
      }
      tileRowIndex += 1
    }
  }

  return cells
}
