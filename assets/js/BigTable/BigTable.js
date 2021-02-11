import PropTypes from 'prop-types'

import { tileRowOrGapType, columnDefinitionType } from './types'
import useFocalCells from './useFocalCells'
import Viewport from './Viewport'

export default function BigTable ({
  sparseTileGrid, nRows, columns, nRowsPerTile, nColumnsPerTile, setWantedTileRange, fixedCellRange = null
}) {
  const { nSkipRows, nSkipColumns, cells, setFocusCellRange } = useFocalCells({
    sparseTileGrid, nRowsPerTile, nColumnsPerTile, setWantedTileRange, fixedCellRange
  })

  return (
    <Viewport
      nRows={nRows}
      columns={columns}
      nSkipRows={nSkipRows}
      nSkipColumns={nSkipColumns}
      cells={cells}
      setFocusCellRange={setFocusCellRange}
    />
  )
}
BigTable.propTypes = {
  sparseTileGrid: PropTypes.arrayOf(tileRowOrGapType.isRequired).isRequired,
  nRows: PropTypes.number.isRequired,
  columns: PropTypes.arrayOf(columnDefinitionType.isRequired).isRequired,
  nRowsPerTile: PropTypes.number.isRequired,
  nColumnsPerTile: PropTypes.number.isRequired,
  fixedCellRange: PropTypes.arrayOf(PropTypes.number.isRequired), // [rowBegin, rowEnd, columnBegin, columnEnd] ... leave null unless unit-testing
  setWantedTileRange: PropTypes.func.isRequired // func(r1, r2, c1, c2) => undefined
}
