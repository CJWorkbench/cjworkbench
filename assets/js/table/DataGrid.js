// ---- DataGrid  ----
// Core table display component.
// Contains all logic that interfaces with react-data-grid
// Paged loading and other logic is in TableView, which is typically our parent

import React from 'react'
import PropTypes from 'prop-types'
import ReactDOM from 'react-dom'
import ReactDataGrid from 'react-data-grid'
import debounce from 'debounce'
import ColumnHeader from './ColumnHeader'
import { RowIndexFormatter, typeToCellFormatter } from './CellFormatters'

// Add row number col and make all cols resizeable
function makeFormattedCols(props) {
  const editable = (props.onEditCell !== undefined) && props.wfModuleId !== undefined; // no wfModuleId means blank table

  const rowNumberColumn = {
    key: props.rowNumKey,
    name: '',
    formatter: RowIndexFormatter,
    width: 40,
    locked: true,
  }

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
    ),
  }))

  return [ rowNumberColumn ].concat(columns)
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
    lastRelevantDeltaId: PropTypes.number, // triggers a render on change
    onEditCell: PropTypes.func,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number,
    showLetter: PropTypes.bool,
    onReorderColumns: PropTypes.func.isRequired,
    onRenameColumn: PropTypes.func.isRequired,
    setDropdownAction: PropTypes.func.isRequired
  }

  constructor(props) {
    super(props)

    this.state = {
      // gridWith and gridHeight start non-0, so rows get rendered in tests
      gridWidth: 100,
      gridHeight : 100,
      componentKey: 0,  // a key for the component; updates if the column header needs
      draggingColumnIndex: null,
    }

    this.onGridRowsUpdated = this.onGridRowsUpdated.bind(this)
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

  // Each ReactDataGrid col needs a unique key. Make one for our row number column
  get rowNumKey() {
    const columnKeys = this.props.columns
    let ret = 'rn_'
    while (columnKeys.includes(ret)) {
      ret += '_'
    }
    return ret
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

  componentDidUpdate (prevProps) {
    if (this.shouldKeyUpdate(prevProps)) {
      this.setState({ componentKey: this.state.componentKey + 1 })
    }
  }

  // Add row number as first column, when we look up data
  getRow = (i) => {
    const row = this.props.getRow(i)
    if (row === null) return null
    // 1 based row numbers
    return { [this.rowNumKey]: i + 1, ...row }
  }

  onGridRowsUpdated({ fromRow, toRow, updated }) {
    if (fromRow !== toRow) {
      // possible if drag handle not hidden, see https://github.com/adazzle/react-data-grid/issues/822
      console.log('More than one row changed at a time in DataGrid, how?')
    }

    if(this.props.isReadOnly) {
      throw new Error("Attempting to edit cells in a read-only workflow.")
    }

    if (this.props.onEditCell)
      var colKey = Object.keys(updated)[0]
      var newVal = updated[colKey]
      this.props.onEditCell(fromRow, colKey, newVal)  // column key is also column name
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

  render() {
    if (this.props.totalRows > 0) {
      const draggingProps = {
        ...this.props,
        rowNumKey: this.rowNumKey,
        onDragStartColumnIndex: this.onDragStartColumnIndex,
        onDragEnd: this.onDragEnd,
        draggingColumnIndex: this.state.draggingColumnIndex,
        onDropColumnIndexAtIndex: this.onDropColumnIndexAtIndex,
        onRenameColumn: this.onRename,
      }
      const columns = makeFormattedCols(draggingProps)

      return(
        <ReactDataGrid
          columns={columns}
          rowGetter={this.getRow}
          rowsCount={this.props.totalRows}
          minWidth={this.state.gridWidth -2}
          minHeight={this.state.gridHeight-2}   // -2 because grid has borders, don't want to expand our parent DOM node
          headerRowHeight={this.props.showLetter ? 68 : 50}
          enableCellSelect={true}
          onGridRowsUpdated={this.onGridRowsUpdated}
          key={this.state.componentKey}
        />
      )
    } else {
      return null
    }
  }
}
