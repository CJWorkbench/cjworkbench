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
export const NRowsPerPage = 200 // exported to help tests
export const FetchTimeout = 0 // ms after scroll before fetch

const getRowSelection = memoize(
  (indexes, onRowsSelected, onRowsDeselected) => ({
    enableShiftSelect: true,
    onRowsSelected,
    onRowsDeselected,
    selectBy: { indexes }
  })
)

function buildEmptyRow (columns) {
  const row = {}

  for (const column of columns) {
    let value
    switch (column.type) {
      case 'text':
        value = ''
        break
      case 'date':
      case 'number':
      case 'timestamp':
      default:
        value = null
        break
    }

    row[column.name] = value
  }

  return row
}

function renderNull () {
  return null
}

function mergeSortedArrays (a, b) {
  const c = []
  for (let i = 0, j = 0; i < a.length || j < b.length;) {
    if (i === a.length) {
      c.push(b[j])
      j += 1
    } else if (j === b.length) {
      c.push(a[i])
      i += 1
    } else {
      if (a[i] === b[j]) {
        c.push(a[i])
        i += 1
        j += 1
      } else if (a[i] < b[i]) {
        c.push(a[i])
        i += 1
      } else {
        c.push(b[j])
        j += 1
      }
    }
  }

  return c
}

class ReactDataGridWithThinnerActionsColumn extends ReactDataGrid {
  _superSetupGridColumns = this.setupGridColumns

  setupGridColumns = (...args) => {
    const ret = this._superSetupGridColumns(...args)
    if (ret[0].cellClass === 'rdg-row-actions-cell') {
      ret[0].width = 40
      ret[0].editable = false
    }
    return ret
  }
}

// --- Main component  ---

export default class DataGrid extends PureComponent {
  static propTypes = {
    loadRows: PropTypes.func.isRequired, // func(startRowInclusive, endRowExclusive) => Promise[Array[Object] or error]
    isReadOnly: PropTypes.bool.isRequired,
    stepId: PropTypes.number, // immutable; null for placeholder table
    columns: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['date', 'text', 'number', 'timestamp']).isRequired
      }).isRequired
    ), // immutable; null for placeholder table
    nRows: PropTypes.number, // immutable; null for placeholder table
    editCell: PropTypes.func.isRequired, // func(fromRow, cellKey, newValue) => undefined
    reorderColumn: PropTypes.func.isRequired, // func(colname, fromIndex, toIndex) => undefined
    onSetSelectedRowIndexes: PropTypes.func.isRequired // func([idx, ...]) => undefined
  }

  state = {
    // gridWith and gridHeight start null, which means DO NOT RENDER. We use
    // this in two ways:
    //
    // 1. We don't render a ReactDataGrid until initial sizing.
    // 2. We defer sizing until after the first render. By waiting a tick, we
    //    let the _rest_ of React's DOM render and be visible to the user. In
    //    other words: we show the spinner -- and wait until that's visible --
    //    before rendering the ReactDataGrid. (ReactDataGrid render can take
    //    >1s when there are many columns.)
    gridWidth: null,
    gridHeight: null,
    spinning: false,
    draggingColumnIndex: null,
    loadedRows: []
  }

  emptyRow = buildEmptyRow(this.props.columns)

  sizerRef = createRef()

  // Cache some data that isn't props or state.
  //
  // Quick refresher: `this.loading` is synchronous; `this.state.loading` is
  // async. In the example
  // `this.setState({ loading: true }); console.log(this.state.loading)`,
  // `console.log` will be called with the _previous_ value of
  // `this.state.loading`, which is not necessarily `true`. That's useless to
  // us. Only fill this.state with stuff we want to render.
  //
  // These values are all set before the initial render(). We want the initial
  // render() to _not_ schedule a load, because we already load in
  // componentDidMount().
  firstMissingRowIndex = 0

  // initial value, for initial load()
  scheduleLoadTimeout = 'init' // initial load() doesn't take a timeout

  load () {
    const min = this.firstMissingRowIndex
    const max = Math.min(min + NRowsPerPage, this.props.nRows || 10)
    const { loadRows } = this.props
    const { loadedRows } = this.state

    if (this.unmounted) return

    let areAllValuesMissing = true
    for (let i = min; i < max; i++) {
      if (loadedRows[i]) {
        areAllValuesMissing = false
        break
      }
    }
    if (areAllValuesMissing) {
      // If we're loading a _subsequent_ page (not the first page), show a
      // spinner.
      if (min > 0) {
        this.setState({ spinning: true })
      }
    }

    loadRows(min, max).then(rows => {
      if (this.unmounted) return

      const loadedRows = this.state.loadedRows.slice()

      for (let i = 0; i < max - min; i++) {
        loadedRows[min + i] = rows[i] || {}
      }

      this.setState(() => {
        this.firstMissingRowIndex = null
        this.scheduleLoadTimeout = null

        return {
          loadedRows,
          spinning: false
        }
      })
    })
  }

  handleGridRowsUpdated = data => {
    const { fromRow, fromRowData, toRow, cellKey, updated } = data

    if (fromRow !== toRow) {
      throw new Error('Attempting to edit more than one cell at a time')
    }

    if (this.props.isReadOnly) {
      throw new Error('Attempting to edit cells in a read-only workflow.')
    }

    const oldValue = String(fromRowData[cellKey])
    const newValue = updated[cellKey]

    if (newValue !== (oldValue || '')) {
      // Edit value in-place in loadedRows. This should jive with getRow()
      // and prevent us from re-rendering the table.
      const mutateStateBecauseReactDataGridMadeUs = this.state.loadedRows[fromRow]
      mutateStateBecauseReactDataGridMadeUs[cellKey] = newValue

      // Edit on the server and in state.
      this.props.editCell(fromRow, cellKey, newValue)
    }
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

  getRow = i => {
    // Be careful. This gets called during render(), so make sure there's
    // nothing in its innards that can ever call setState().
    //
    // react-data-grid should have the motto: Not For Dynamic Data.
    const { loadedRows } = this.state

    if (loadedRows[i]) {
      return loadedRows[i]
    } else {
      // We'll return an empty row for now. But what _else_ will we do?
      if (this.unmounted) {
        // Don't load
      } else if (!this.props.stepId) {
        // This is a placeholder table, not a real data table. Don't load.
      } else if (!this.scheduleLoadTimeout) {
        this.firstMissingRowIndex = i
        this.scheduleLoadTimeout = window.setTimeout(
          () => this.load(),
          FetchTimeout
        )
      } else {
        // We've already scheduled a load. No-op: when the load returns,
        // we'll render(), and that will call getRow() again, and that can
        // schedule the next fetch().
      }

      // Return something right now, in the meantime
      return this.emptyRow
    }
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
        selectAllRenderer={renderNull}
        onGridRowsUpdated={this.handleGridRowsUpdated}
        enableRowSelect
        rowRenderer={Row}
      />
    )
  }

  render () {
    const { spinning, gridWidth, gridHeight } = this.state

    // Don't render when gridWidth===null. We only render after a setTimeout
    // in updateSize(). That way, React can handle the rest of the DOM updates
    // that a click event entails without spending entire seconds on
    // react-data-grid.
    //
    // The net effect: we render after the spinner appears. This is much more
    // usable.
    //
    // Beware: gridWidth = gridHeight = 0 in Enzyme tests with a fake DOM.
    return (
      <div className='data-grid-sizer' ref={this.sizerRef}>
        {gridWidth !== null && gridHeight !== null ? this.renderGrid() : null}
        {spinning ? <Spinner /> : null}
      </div>
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
  onTableLoaded: PropTypes.func // func({ stepSlug, deltaId }) => undefined
}
