// ---- DataGrid  ----
// Core table display component.
// Contains all logic that interfaces with react-data-grid
// Paged loading and other logic is in TableView, which is typically our parent

import React from 'react'
import PropTypes from 'prop-types'
import ReactDOM from 'react-dom'
import ReactDataGrid from 'react-data-grid'
import debounce from 'debounce'
import memoize from 'memoize-one'
import ColumnHeader from './ColumnHeader'
import Row from './Row'
import RowActionsCell from './RowActionsCell'
import { typeToCellFormatter } from './CellFormatters'

const getRowSelection = memoize((indexes, onRowsSelected, onRowsDeselected) => ({
  enableShiftSelect: true,
  onRowsSelected,
  onRowsDeselected,
  selectBy: { indexes }
}))

function renderNull () {
  return null
}

function mergeSortedArrays (a, b) {
  const c = []
  for (let i = 0, j = 0; i < a.length || j < b.length; ) {
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

// Add row number col and make all cols resizeable
function makeFormattedCols(props) {
  const editable = (props.onEditCell !== undefined) && props.wfModuleId !== undefined; // no wfModuleId means blank table

  // We can have an empty table, but we need to give these props to ColumnHeader anyway
  const safeColumns = props.columns || []
  const columnTypes = props.columnTypes || safeColumns.map(_ => '')
  const showLetter = props.showLetter || false

  const columns = safeColumns.map((columnKey, index) => ({
    key: columnKey,
    name: columnKey,
    resizable: true,
    editable: editable,
    formatter: typeToCellFormatter(columnTypes[index]),
    width: 160,
    // react-data-grid normally won't re-render if we change headerRenderer.
    // So we need to change _other_ props, forcing it to re-render.
    maybeTriggerRenderIfChangeDraggingColumnIndex: props.draggingColumnIndex,
    maybeTriggerRenderIfChangeIsSorted: (props.sortColumn === columnKey),
    maybeTriggerRenderIfChangeSortDirection: props.sortDirection,
    maybeTriggerRenderIfChangeShowLetter: props.showLetter,
    headerRenderer: (
      <ColumnHeader
        columnKey={columnKey}
        columnType={columnTypes[index]}
        index={index}
        isSorted={props.sortColumn === columnKey}
        sortDirection={props.sortDirection}
        showLetter={showLetter}
        onDragStartColumnIndex={props.onDragStartColumnIndex}
        onDragEnd={props.onDragEnd}
        draggingColumnIndex={props.draggingColumnIndex}
        onDropColumnIndexAtIndex={props.onDropColumnIndexAtIndex}
        onRenameColumn={props.onRenameColumn}
        isReadOnly={props.isReadOnly}
        setDropdownAction={props.setDropdownAction}
      />
    )
  }))

  return columns
}


// --- Main component  ---

export default class DataGrid extends React.Component {
  static propTypes = {
    totalRows: PropTypes.number.isRequired,
    getRow: PropTypes.func.isRequired,
    columns: PropTypes.array.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    columnTypes: PropTypes.array,     // not required if blank table
    wfModuleId: PropTypes.number,    // not required if blank table
    onEditCell: PropTypes.func,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number,
    showLetter: PropTypes.bool,
    onReorderColumns: PropTypes.func.isRequired,
    onRenameColumn: PropTypes.func.isRequired,
    setDropdownAction: PropTypes.func.isRequired,
    selectedRowIndexes: PropTypes.arrayOf(PropTypes.number.isRequired).isRequired, // may be empty
    onSetSelectedRowIndexes: PropTypes.func.isRequired // func([idx, ...]) => undefined
  }

  state = {
    // gridWith and gridHeight start non-0, so rows get rendered in tests
    gridWidth: 100,
    gridHeight : 100,
    draggingColumnIndex: null
  }

  // After the component mounts, and on any change, set the height to parent div height
  updateSize = () => {
    const domNode = ReactDOM.findDOMNode(this)
    if (domNode && domNode.parentElement) {
      const container = domNode.parentElement
      const gridHeight = Math.max(100, container.offsetHeight)
      const gridWidth = Math.max(100, container.offsetWidth)
      this.setState({ gridWidth, gridHeight })
    }
  }

  componentDidMount() {
    this._resizeListener = debounce(this.updateSize, 50)
    window.addEventListener("resize", this._resizeListener)
    this.updateSize()
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this._resizeListener)
  }

  // Check if column names are changed between props, used for shouldKeyUpdate
  columnsChanged (prevProps, nextProps) {
    const prevColumns = prevProps.columns || null
    const nextColumns = nextProps.columns || null
    const prevTypes = prevProps.columnTypes || null
    const nextTypes = nextProps.columnTypes || null

    if (prevColumns === nextColumns && prevTypes === nextTypes) {
      return false
    }

    if (prevColumns === null || nextColumns === null || prevTypes === null || nextTypes === null) {
      return true
    }

    if (prevColumns.length !== nextColumns.length) {
      return true
    }

    for (let i = 0; i < prevColumns.length; i++) {
      if (prevColumns[i] !== nextColumns[i] || prevTypes[i] !== nextTypes[i]) {
        return true
      }
    }

    return false
  }

  shouldKeyUpdate (prevProps) {
    if (this.props.sortColumn !== prevProps.sortColumn) {
      return true
    }
    if (this.props.sortDirection !== prevProps.sortDirection) {
      return true
    }
    if (this.props.showLetter !== prevProps.showLetter) {
      return true
    }
    // For some reason, react-data-grid does not change column order
    // in its output when the column order changes when custom header renderer
    // is involved, so we bump the key if columns are changed
    if (this.columnsChanged(prevProps, this.props)) {
      return true
    }
    return false
  }

  onGridRowsUpdated = (data, ...args) => {
    const { fromRow, fromRowData, toRow, cellKey, updated } = data

    if (fromRow !== toRow) {
      throw new Error('Attempting to edit more than one cell at a time')
    }

    if (this.props.isReadOnly) {
      throw new Error('Attempting to edit cells in a read-only workflow.')
    }

    if (this.props.onEditCell) {
      const oldValue = String(fromRowData[cellKey])
      const newValue = updated[cellKey]

      if (newValue !== oldValue) {
        this.props.onEditCell(fromRow, cellKey, newValue)
      }
    }
  }

  onDropColumnIndexAtIndex = (fromIndex, toIndex) => {
    const sourceKey = this.props.columns[fromIndex]
    let reorderInfo = {
        column: sourceKey,
        from: fromIndex,
        to: toIndex,
      }

    this.props.onReorderColumns(this.props.wfModuleId, 'reorder-columns', false, reorderInfo)
  }

  onDragStartColumnIndex = (index) => {
    this.setState({
      draggingColumnIndex: index,
    })
  }

  onDragEnd = () => {
    this.setState({
      draggingColumnIndex: null,
    })
  }

  onRename = (renameInfo) => {
    this.props.onRenameColumn(this.props.wfModuleId, 'rename-columns', false, renameInfo)
  }

  onRowsSelected = (newRows) => {
    // Merge is O(n lg n), better than O(n^2) of naive algo
    const newIndexes = newRows.map(r => r.rowIdx).sort()
    const oldIndexes = this.props.selectedRowIndexes.slice().sort()
    const indexes = mergeSortedArrays(oldIndexes, newIndexes)
    this.props.onSetSelectedRowIndexes(indexes)
  }

  onRowsDeselected = (rows) => {
    // Nix by hash-map is slow, but it scales O(n) and we need that
    const nix = {}
    for (let i = 0; i < rows.length; i++) {
      nix[String(rows[i].rowIdx)] = null
    }

    const selectedRowIndexes = this.props.selectedRowIndexes
      .filter(i => !nix.hasOwnProperty(String(i)))
    this.props.onSetSelectedRowIndexes(selectedRowIndexes)
  }

  render () {
    if (!this.props.totalRows) {
      return null
    }

    const { selectedRowIndexes } = this.props

    const draggingProps = {
      ...this.props,
      onDragStartColumnIndex: this.onDragStartColumnIndex,
      onDragEnd: this.onDragEnd,
      draggingColumnIndex: this.state.draggingColumnIndex,
      onDropColumnIndexAtIndex: this.onDropColumnIndexAtIndex,
      onRenameColumn: this.onRename,
    }
    const columns = makeFormattedCols(draggingProps)
    const rowSelection = getRowSelection(selectedRowIndexes, this.onRowsSelected, this.onRowsDeselected)

    return(
      <ReactDataGridWithThinnerActionsColumn
        columns={columns}
        rowActionsCell={RowActionsCell}
        rowGetter={this.props.getRow}
        rowsCount={this.props.totalRows}
        minWidth={this.state.gridWidth - 2}
        minHeight={this.state.gridHeight - 2}   // -2 because grid has borders, don't want to expand our parent DOM node
        headerRowHeight={this.props.showLetter ? 68 : 50}
        enableCellSelect={true}
        selectAllRenderer={renderNull}
        onGridRowsUpdated={this.onGridRowsUpdated}
        enableRowSelect={true}
        rowRenderer={Row}
        rowSelection={rowSelection}
      />
    )
  }
}
