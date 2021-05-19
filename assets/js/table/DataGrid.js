// ---- DataGrid  ----
// Core table display component.
// Contains all logic that interfaces with react-data-grid
// Paged loading and other logic is in TableView, which is typically our parent

import React from 'react'
import PropTypes from 'prop-types'
import BigTable from '../BigTable'
import useTiles from '../BigTable/useTiles'
import { columnToCellFormatter } from '../Report/CellFormatters2'
import ColumnHeader from './ColumnHeader'
// import RowActionsCell from './RowActionsCell'
import propTypes from '../propTypes'

function stub () {}

function buildColumnHeaderComponent (props) {
  const { column, ...rest } = props
  return () => (
    <ColumnHeader
      columnKey={column.name}
      columnType={column.type}
      dateUnit={column.dateUnit}
      onDragStartColumnIndex={stub}
      onDragEnd={stub}
      onDropColumnIndexAtIndex={stub}
      {...rest}
    />
  )
}

/*

export default class DataGrid extends PureComponent {
  static propTypes = {
    stepId: PropTypes.number, // immutable; null for placeholder table
    reorderColumn: PropTypes.func.isRequired, // func(colname, fromIndex, toIndex) => undefined
    onSetSelectedRowIndexes: PropTypes.func.isRequired // func([idx, ...]) => undefined
  }

  state = {
    draggingColumnIndex: null,
  }

  handleDropColumnIndexAtIndex = (fromIndex, toIndex) => {
    const colname = this.props.columns[fromIndex].name
    this.props.reorderColumn(colname, fromIndex, toIndex)
  }

  handleDragStartColumnIndex = index => {
    this.setState({
      draggingColumnIndex: index
    })
  }

  handleDragEnd = () => {
    this.setState({
      draggingColumnIndex: null
    })
  }

  // Add row number col and make all cols resizeable
  makeFormattedCols = memoize(draggingColumnIndex => {
    // immutable props
    const { isReadOnly, columns, stepId } = this.props

    return columns.map((column, index) => ({
      key: column.name,
      name: column.name,
      resizable: true,
      editable: !isReadOnly,
      formatter: columnToCellFormatter(column),
      width: 180,
      // react-data-grid normally won't re-render if we change headerRenderer.
      // So we need to change _other_ props, forcing it to re-render.
      maybeTriggerRenderIfChangeDraggingColumnIndex: draggingColumnIndex,
      headerRenderer: (
        <ColumnHeader
          stepId={stepId}
          columnKey={column.name}
          columnType={column.type}
          dateUnit={column.unit || null}
          index={index}
          onDragStartColumnIndex={this.handleDragStartColumnIndex}
          onDragEnd={this.handleDragEnd}
          draggingColumnIndex={draggingColumnIndex}
          onDropColumnIndexAtIndex={this.handleDropColumnIndexAtIndex}
          isReadOnly={isReadOnly}
        />
      )
    }))
  })

  renderGrid () {
    const { gridWidth, gridHeight } = this.state
    const { nRows } = this.props

    const formattedColumns = this.makeFormattedCols(
      this.state.draggingColumnIndex
    )

    return (
      <ReactDataGridWithThinnerActionsColumn
        columns={formattedColumns}
        rowActionsCell={RowActionsCell}
        rowGetter={this.getRow}
        rowsCount={nRows}
        minWidth={gridWidth}
        minHeight={gridHeight}
        headerRowHeight={68}
        enableCellAutoFocus={false}
        enableCellSelect
        onGridRowsUpdated={this.handleGridRowsUpdated}
        enableRowSelect
        rowRenderer={Row}
      />
    )
  }
}
*/

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
    isReadOnly
  } = props

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
  const bigColumns = React.useMemo(
    () => columns.map((column, index) => ({
      ...column,
      width: 180,
      headerComponent: buildColumnHeaderComponent({ column, index, stepId, stepSlug, isReadOnly }),
      valueComponent: columnToCellFormatter(column)
    })),
    [columns, stepId, stepSlug, isReadOnly]
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
