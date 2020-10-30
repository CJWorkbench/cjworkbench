export default function findWantedLoadingTile (sparseTileGrid, r1, r2, c1, c2) {
  if (sparseTileGrid.tileRows.length === 0) {
    return null
  }

  const { tileRows } = sparseTileGrid
  let r = 0
  let tileColumns
  for (let i = 0; i < tileRows.length && r < r2; i++) {
    const item = tileRows[i]
    if (Number.isInteger(item)) {
      // gap
      r += item
    } else {
      if (r >= r1) {
        tileColumns = item
        for (let j = c1; j < c2; j++) {
          if (tileColumns[j].type === 'loading') {
            return tileColumns[j]
          }
        }
      }
      r += 1
    }
  }

  return null
}
