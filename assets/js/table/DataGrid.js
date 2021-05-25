import React from 'react'
import PropTypes from 'prop-types'
import BigTable from '../BigTable'
import useTiles from '../BigTable/useTiles'
import { columnToCellFormatter } from '../Report/CellFormatters2'
import ColumnHeader from './ColumnHeader'
import propTypes from '../propTypes'

export default function DataGrid (props) {
  const {
    workflowIdOrSecretId,
    stepId,
    stepSlug,
    deltaId,
    columns,
    nRows,
    nColumnsPerTile,
    nRowsPerTile,
    onTableLoaded,
    onEdit,
    onReorder,
    isReadOnly
  } = props

  const [draggingColumnIndex, setDraggingColumnIndex] = React.useState(null)
  const nTileRows = Math.ceil(nRows / nRowsPerTile)
  const nTileColumns = Math.ceil(columns.length / nColumnsPerTile)
  const fetchTile = React.useCallback(
    (tileRow, tileColumn, fetchOptions) => {
      const url = `/workflows/${workflowIdOrSecretId}/tiles/${stepSlug}/delta-${deltaId}/${tileRow},${tileColumn}.json`
      return global.fetch(url, fetchOptions)
    },
    [workflowIdOrSecretId, stepSlug, deltaId]
  )
  const { sparseTileGrid, setWantedTileRange } = useTiles({ fetchTile, nTileRows, nTileColumns })

  const handleDragStartColumnIndex = setDraggingColumnIndex
  const handleDragEnd = React.useCallback(
    () => setDraggingColumnIndex(null),
    [setDraggingColumnIndex]
  )
  const handleDropColumnIndex = React.useCallback(
    index => { onReorder(columns[draggingColumnIndex].name, draggingColumnIndex, index) },
    [onReorder, columns, draggingColumnIndex]
  )

  const bigColumns = React.useMemo(
    () => columns.map((column, index) => ({
      ...column,
      width: 180,
      headerComponent: ColumnHeader,
      headerProps: {
        columnKey: column.name,
        columnType: column.type,
        dateUnit: column.dateUnit,
        index,
        stepId,
        stepSlug,
        isReadOnly,
        draggingColumnIndex,
        onDragStartColumnIndex: handleDragStartColumnIndex,
        onDragEnd: handleDragEnd,
        onDropColumnIndex: handleDropColumnIndex
      },
      valueComponent: columnToCellFormatter(column)
    })),
    [columns, stepId, stepSlug, draggingColumnIndex, handleDragStartColumnIndex, handleDropColumnIndex, handleDragEnd, isReadOnly]
  )

  React.useEffect(() => {
    if (sparseTileGrid.length && sparseTileGrid[0][0] !== null && onTableLoaded) {
      onTableLoaded({ stepSlug, deltaId })
    }
  }, [sparseTileGrid, onTableLoaded, stepSlug, deltaId])

  return (
    <BigTable
      sparseTileGrid={sparseTileGrid}
      nRows={nRows}
      columns={bigColumns}
      nRowsPerTile={nRowsPerTile}
      nColumnsPerTile={nColumnsPerTile}
      setWantedTileRange={setWantedTileRange}
      onEdit={onEdit}
    />
  )
}
DataGrid.propTypes = {
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  stepSlug: PropTypes.string.isRequired,
  stepId: PropTypes.number.isRequired,
  deltaId: PropTypes.number.isRequired,
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['date', 'text', 'number', 'timestamp']).isRequired
    }).isRequired
  ), // immutable; null for placeholder table
  nRows: PropTypes.number, // immutable; null for placeholder table
  nColumnsPerTile: PropTypes.number.isRequired,
  nRowsPerTile: PropTypes.number.isRequired,
  onTableLoaded: PropTypes.func, // func({ stepSlug, deltaId }) => undefined
  onEdit: PropTypes.func // func({ row, column, oldValue, newValue }) => undefined, or null
}
