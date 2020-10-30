export default function findWantedLoadingTile (tileRows, r1, r2, c1, c2) {
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
          if (tileColumns[j] === null) {
            return { tileRow: r, tileColumn: j }
          }
        }
      }
      r += 1
    }
  }

  return null
}
