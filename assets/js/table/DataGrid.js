// ---- DataGrid  ----
// Core table display component.
// Contains all logic that interfaces with react-data-grid
// Paged loading and other logic is in TableView, which is typically our parent

import { createRef, PureComponent } from 'react'
import PropTypes from 'prop-types'
import ReactDataGrid from 'react-data-grid'
import debounce from 'debounce'
import memoize from 'memoize-one'
import Spinner from '../Spinner'
import ColumnHeader from './ColumnHeader'
import Row from './Row'
import RowActionsCell from './RowActionsCell'
import { columnToCellFormatter } from './CellFormatters'

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
      case 'number':
        value = null
        break
      case 'timestamp':
        value = null
        break
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

/**
 * ReactDataGrid, with a thinner hard-coded actions-column width.
 */
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
        type: PropTypes.oneOf(['text', 'number', 'timestamp']).isRequired
      }).isRequired
    ), // immutable; null for placeholder table
    nRows: PropTypes.number, // immutable; null for placeholder table
    editCell: PropTypes.func.isRequired, // func(fromRow, cellKey, newValue) => undefined
    reorderColumn: PropTypes.func.isRequired, // func(colname, fromIndex, toIndex) => undefined
    selectedRowIndexes: PropTypes.arrayOf(PropTypes.number.isRequired)
      .isRequired, // may be empty
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

  // After the component mounts, and on any change, set the height to parent div height
  updateSize = () => {
    const domNode = this.sizerRef.current
    if (domNode && domNode.parentElement) {
      const gridHeight = Math.max(100, domNode.offsetHeight)
      const gridWidth = Math.max(100, domNode.offsetWidth)
      window.setTimeout(() => {
        if (this.unmounted) return
        this.setState({ gridWidth, gridHeight })
      }, 0)
    }
  }

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

  componentDidMount () {
    if (this.props.nRows > 0) {
      this.load()
    }

    this._resizeListener = debounce(this.updateSize, 50)
    window.addEventListener('resize', this._resizeListener)
    this.updateSize()
  }

  componentWillUnmount () {
    window.removeEventListener('resize', this._resizeListener)
    this.unmounted = true
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

  onRowsSelected = newRows => {
    // Merge is O(n lg n), better than O(n^2) of naive algo
    const newIndexes = newRows.map(r => r.rowIdx).sort()
    const oldIndexes = this.props.selectedRowIndexes.slice().sort()
    const indexes = mergeSortedArrays(oldIndexes, newIndexes)
    this.props.onSetSelectedRowIndexes(indexes)
  }

  onRowsDeselected = rows => {
    // Nix by hash-map is slow, but it scales O(n) and we need that
    const nix = {}
    for (let i = 0; i < rows.length; i++) {
      nix[String(rows[i].rowIdx)] = null
    }

    const selectedRowIndexes = this.props.selectedRowIndexes.filter(
      i => !Object.prototype.hasOwnProperty.call(nix, String(i))
    )
    this.props.onSetSelectedRowIndexes(selectedRowIndexes)
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
    const { selectedRowIndexes, nRows } = this.props

    const formattedColumns = this.makeFormattedCols(
      this.state.draggingColumnIndex
    )
    const rowSelection = getRowSelection(
      selectedRowIndexes,
      this.onRowsSelected,
      this.onRowsDeselected
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
        rowSelection={rowSelection}
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
