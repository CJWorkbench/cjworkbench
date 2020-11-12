import React from 'react'
import getCellRange from './getCellRange'

/**
 * Convert sparseTileGrid to { nSkipRows, nSkipColumns, cells }
 */
export default function useFocalCells ({ sparseTileGrid, nRowsPerTile, nColumnsPerTile, setWantedTileRange, fixedCellRange = null }) {
  // Begin with at least one cell visible (if there are enough rows). Viewport.js
  // will use its height for resize calculations.
  const [dynamicCellRange, setCellRange] = React.useState([0, sparseTileGrid.length > 0 ? 1 : 0, 0, 1])
  const setFocusCellRange = React.useCallback((...range) => {
    if (
      // Conditional on changes. The component that calls useFocalCells()
      // shouldn't need to re-render for spurious setCellRange() calls.
      range[0] !== dynamicCellRange[0] ||
      range[1] !== dynamicCellRange[1] ||
      range[2] !== dynamicCellRange[2] ||
      range[3] !== dynamicCellRange[3]
    ) {
      setCellRange(range)
      setWantedTileRange(
        Math.floor(range[0] / nRowsPerTile),
        Math.ceil(range[1] / nRowsPerTile),
        Math.floor(range[2] / nColumnsPerTile),
        Math.ceil(range[3] / nColumnsPerTile)
      )
    }
  }, [setCellRange])

  const cellRange = fixedCellRange === null ? dynamicCellRange : fixedCellRange
  const cells = React.useMemo(
    () => getCellRange(sparseTileGrid, nRowsPerTile, nColumnsPerTile, ...cellRange),
    [sparseTileGrid, nRowsPerTile, nColumnsPerTile, ...cellRange]
  )

  return {
    nSkipColumns: cellRange[2],
    nSkipRows: cellRange[0],
    cells,
    setFocusCellRange
  }
}
