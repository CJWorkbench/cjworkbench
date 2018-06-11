// ---- DataGrid  ----
// Core table display component.
// Contains all logic that interfaces with react-data-grid
// Paged loading and other logic is in TableView, which is typically our parent

import React from 'react'
import ReactDOM from 'react-dom'
import ReactDataGrid, { HeaderCell } from 'react-data-grid'
import {idxToLetter} from "./utils";
import PropTypes from 'prop-types'
import debounce from 'lodash/debounce'


// --- Row and column formatting ---

// Custom Formatter component, to render row number in a different style
export class RowNumberFormatter extends React.PureComponent {

  render() {

    var rowNumber = this.props.value;
    var rowNumberDigits = rowNumber.toString().length;
    var numberClass = 'row-number';
    if (rowNumberDigits > 2 && rowNumberDigits < 7 ) {
      numberClass = 'row-number-' + rowNumberDigits;
    } else if (rowNumberDigits >= 7) {
      numberClass = 'row-number-6'
    }

    return (
      <div className={numberClass}>
        {rowNumber}
      </div>)
  }
}

RowNumberFormatter.propTypes = {
  value:    PropTypes.node.isRequired
};


class ReorderColumnDropZone extends React.PureComponent {
  static propTypes = {
    leftOrRight: PropTypes.oneOf([ 'left', 'right' ]).isRequired,
    fromIndex: PropTypes.number.isRequired,
    toIndex: PropTypes.number.isRequired,
    onDropColumnIndexAtIndex: PropTypes.func.isRequired, // func(fromIndex, toIndex) => undefined
  }

  constructor(props) {
    super(props)

    this.state = {
      isDragHover: false,
    }
  }

  onDragEnter = (ev) => {
    this.setState({
      isDragHover: true,
    })
  }

  onDragLeave = (ev) => {
    this.setState({
      isDragHover: false,
    })
  }

  onDragOver = (ev) => {
    ev.preventDefault() // allow drop by preventing the default, which is "no drop"
  }

  onDrop = (ev) => {
    const { fromIndex, toIndex, onDropColumnIndexAtIndex } = this.props
    onDropColumnIndexAtIndex(fromIndex, toIndex)
  }

  render() {
    let className = 'column-reorder-drop-zone'
    className += ' align-' + this.props.leftOrRight
    if (this.state.isDragHover) className += ' drag-hover'

    return (
      <div
        className={className}
        onDragEnter={this.onDragEnter}
        onDragLeave={this.onDragLeave}
        onDragOver={this.onDragOver}
        onDrop={this.onDrop}
        >
      </div>
    )
  }
}

export class EditableColumnName extends React.Component {
  static propTypes = {
    columnKey: PropTypes.string.isRequired,
    onRename: PropTypes.func.isRequired,
    isReadOnly: PropTypes.bool.isRequired
  };

  constructor(props) {
    super(props);

    this.state = {
      newName: props.columnKey,
      editMode: false,
    };

    this.enterEditMode = this.enterEditMode.bind(this);
    this.handleInputChange = this.handleInputChange.bind(this);
    this.handleInputBlur = this.handleInputBlur.bind(this);
    this.handleInputKeyDown = this.handleInputKeyDown.bind(this);
    this.handleInputFocus = this.handleInputFocus.bind(this);
  }

  enterEditMode() {
    if(!this.props.isReadOnly) {
      this.setState({editMode: true});
    }
  }

  exitEditMode() {
    this.setState({editMode: false});
  }

  handleInputChange(event) {
    this.setState({newName: event.target.value});
  }

  handleInputCommit() {
    this.setState({
        newName: this.state.newName,
        editMode: false
    });
    if(this.state.newName != this.props.columnKey) {
      this.props.onRename({
        prevName: this.props.columnKey,
        newName: this.state.newName
      });
    }
  }

  handleInputBlur() {
    this.handleInputCommit();
  };

  handleInputKeyDown(event) {
    // Changed to keyDown as esc does not fire keyPress
    if(event.key == 'Enter') {
      this.handleInputCommit();
    } else if (event.key == 'Escape') {
      this.setState({newName: this.props.columnKey});
      this.exitEditMode();
    }
  }

  handleInputFocus(event) {
    event.target.select();
  }

  render() {
    if(this.state.editMode) {
      // The class name 'column-key-input' is used in
      // the code to prevent dragging while editing,
      // please keep it as-is.
      return (
        <input
          className={'column-key column-key-input'}
          type={'text'}
          value={this.state.newName}
          onChange={this.handleInputChange}
          onBlur={this.handleInputBlur}
          onKeyDown={this.handleInputKeyDown}
          onFocus={this.handleInputFocus}
        />
      );
    } else {
      return (
        <span
          className={'column-key'}
          onClick={this.enterEditMode}
        >
          {this.state.newName}
        </span>
      );
    }
  }
}

// Sort arrows, A-Z letter identifiers
export class ColumnHeader extends React.PureComponent {
  static propTypes = {
    columnKey: PropTypes.string.isRequired,
    columnType: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    index: PropTypes.number.isRequired,
    isSorted: PropTypes.bool.isRequired,
    sortDirection: PropTypes.oneOf([ 'NONE', 'ASC', 'DESC' ]), // not required, which is weird
    onSortColumn: PropTypes.func.isRequired,
    showLetter: PropTypes.bool.isRequired,
    onDragStartColumnIndex: PropTypes.func.isRequired, // func(index) => undefined
    onDragEnd: PropTypes.func.isRequired, // func() => undefined
    onDropColumnIndexAtIndex: PropTypes.func.isRequired, // func(from, to) => undefined
    draggingColumnIndex: PropTypes.number, // if set, we are dragging
    onRenameColumn: PropTypes.func,
  };

  constructor(props) {
    super(props);

    this.state = {
      isHovered: false,
      newName: props.columnKey
    };
  }

  onClickSort = () => {
    if(!this.props.isReadOnly) {
      this.props.onSortColumn(this.props.columnKey, this.props.columnType);
    }
  }

  onMouseEnter = () => {
    this.setState({isHovered: true});
  }

  onMouseLeave = () => {
    this.setState({isHovered: false});
  }

  onDragStart = (ev) => {
    if(this.props.isReadOnly) {
      ev.preventDefault();
      return;
    }

    if(ev.target.classList.contains('column-key-input')) {
      ev.preventDefault();
      return;
    }

    this.props.onDragStartColumnIndex(this.props.index)

    ev.dataTransfer.effectAllowed = [ 'move' ]
    ev.dataTransfer.dropEffect = 'move'
    ev.dataTransfer.setData('text/plain', this.props.columnKey)
  }

  onDragEnd = () => {
    this.props.onDragEnd()
  }

  renderSortArrow() {
    if(this.props.isReadOnly) {
      return '';
    }

    const {
      columnKey,
      columnType,
      isSorted,
      sortDirection,
      index,
    } = this.props

    let sortDirectionClass = '';

    // If we change the sort icon, change the class names here.
    const sortDirectionDict = {
      'NONE': '',
      'ASC': 'icon-sort-up',
      'DESC': 'icon-sort-down',
    };

    if (isSorted && (sortDirection != 'NONE')) {
      // If column is sorted, set the direction to current sort direction
      sortDirectionClass = sortDirectionDict[sortDirection];
    } else if (this.state.isHovered) {
      // If there is no sort but column is hovered, set to "default" sort direction
      if (['Number', 'Date'].indexOf(columnType) >= 0) {
        sortDirectionClass = sortDirectionDict['DESC'];
      } else if (['String'].indexOf(columnType) >= 0) {
        sortDirectionClass = sortDirectionDict['ASC'];
      }
    }

    if (sortDirectionClass.length > 0) {
      return (
        <button title="Sort" className='column-sort-arrow' onClick={this.onClickSort}>
          <i className={sortDirectionClass}></i>
        </button>
      );
    }
    return '';
  }

  renderLetter() {
    if (this.props.showLetter) {
      return (
          // The 'column-letter' class name is used in the test so please be careful with it
          <div className='column-letter'>
            {idxToLetter(this.props.index)}
          </div>
      );
    } else {
      return null
    }
  }

  render() {
    const {
      columnKey,
      columnType,
      index,
      onDropColumnIndexAtIndex,
      draggingColumnIndex,
    } = this.props

    const sortArrowSection = this.renderSortArrow();
    const letterSection = this.renderLetter();

    function maybeDropZone(leftOrRight, toIndex) {
      if (draggingColumnIndex === null) return null
      if (draggingColumnIndex === toIndex) return null

      // Also, dragging to fromIndex+1 is a no-op
      if (draggingColumnIndex === toIndex - 1) return null

      return (
        <ReorderColumnDropZone
          leftOrRight={leftOrRight}
          fromIndex={draggingColumnIndex}
          toIndex={toIndex}
          onDropColumnIndexAtIndex={onDropColumnIndexAtIndex}
          />
      )
    }

    const draggingClass = (draggingColumnIndex === index) ? 'dragging' : ''


    //<span className="column-key">{columnKey}</span>
    return (
      <React.Fragment>
        {letterSection}
        <div
          className={`data-grid-column-header ${draggingClass}`}
          onMouseEnter={this.onMouseEnter}
          onMouseLeave={this.onMouseLeave}
          draggable={true}
          onDragStart={this.onDragStart}
          onDragEnd={this.onDragEnd}
          >
          {maybeDropZone('left', index)}
          <div className="sort-container">
            <EditableColumnName columnKey={columnKey} onRename={this.props.onRenameColumn} isReadOnly={this.props.isReadOnly}/>
            {sortArrowSection}
          </div>
          {maybeDropZone('right', index + 1)}
        </div>
      </React.Fragment>
    );
  }
}


// Add row number col and make all cols resizeable
function makeFormattedCols(props) {
  const editable = (props.onEditCell !== undefined) && props.wfModuleId !== undefined; // no wfModuleId means blank table

  const rowNumberColumn = {
    key: props.rowNumKey,
    name: '',
    formatter: RowNumberFormatter,
    width: 40,
    locked: true,
  }

  const columns = props.columns.map((columnKey, index) => ({
    key: columnKey,
    name: columnKey,
    resizable: true,
    editable: editable,
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
        columnType={props.columnTypes[index]}
        index={index}
        isSorted={props.sortColumn === columnKey}
        sortDirection={props.sortDirection}
        onSortColumn={props.onSortColumn}
        showLetter={props.showLetter}
        onDragStartColumnIndex={props.onDragStartColumnIndex}
        onDragEnd={props.onDragEnd}
        draggingColumnIndex={props.draggingColumnIndex}
        onDropColumnIndexAtIndex={props.onDropColumnIndexAtIndex}
        onRenameColumn={props.onRenameColumn}
        isReadOnly={props.isReadOnly}
        />
    ),
  }))

  return [ rowNumberColumn ].concat(columns)
}


// --- Main component  ---

export default class DataGrid extends React.Component {
  static propTypes = {
    totalRows:          PropTypes.number.isRequired,
    getRow:             PropTypes.func.isRequired,
    columns:            PropTypes.array.isRequired,
    isReadOnly:         PropTypes.bool.isRequired,
    columnTypes:        PropTypes.array,     // not required if blank table
    wfModuleId:         PropTypes.number,    // not required if blank table
    revision:           PropTypes.number,
    resizing:           PropTypes.bool,
    onEditCell:         PropTypes.func,
    onSortColumn:       PropTypes.func,
    sortColumn:         PropTypes.string,
    sortDirection:      PropTypes.string,
    showLetter:         PropTypes.bool,
    onReorderColumns:   PropTypes.func,
    onRenameColumn:     PropTypes.func,
  };

  constructor(props) {
    super(props);

    this.state = {
      gridHeight : 100,  // arbitrary, reset at componentDidMount, but non-zero means we get row elements in testing
      componentKey: 0,  // a key for the component; updates if the column header needs
      draggingColumnIndex: null,
    };

    this.updateSize = this.updateSize.bind(this);
    this.getRow = this.getRow.bind(this);
    this.onGridRowsUpdated = this.onGridRowsUpdated.bind(this);
  }

  // After the component mounts, and on any change, set the height to parent div height
  updateSize() {
    var domNode = ReactDOM.findDOMNode(this);
    if (domNode) {
      var gridHeight = domNode.parentElement.offsetHeight;
      var gridWidth = domNode.parentElement.offsetWidth;
      this.setState({
        gridHeight: gridHeight,
        gridWidth: gridWidth
      });
    }
  }

  // Each ReactDataGrid col needs a unique key. Make one for our row number column
  get rowNumKey() {
    const columnKeys = this.props.columns
    let ret = 'rn_';
    while (columnKeys.includes(ret)) {
      ret += '_';
    }
    return ret;
  }

  componentDidMount() {
    this._resizeListener = debounce(this.updateSize, 200);
    window.addEventListener("resize", this._resizeListener);
    this.updateSize();
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this._resizeListener);
  }

  // Check if column names are changed between props, used for shouldKeyUpdate
  columnsChanged(prevColumns, nextColumns) {
    if((prevColumns == null) || (nextColumns == null)) {
      return true;
    }
    if(prevColumns.length != nextColumns.length) {
      return true;
    }
    for(var i = 0; i < prevColumns.length; i ++) {
      if(prevColumns[i] != nextColumns[i]) {
        return true;
      }
    }
    return false;
  }

  shouldKeyUpdate(nextProps) {
    if(this.props.sortColumn != nextProps.sortColumn) {
      return true;
    }
    if(this.props.sortDirection != nextProps.sortDirection) {
      return true;
    }
    if(this.props.showLetter != nextProps.showLetter) {
      return true;
    }
    // For some reason, react-data-grid does not change column order
    // in its output when the column order changes when custom header renderer
    // is involved, so we bump the key if columns are changed
    if(this.columnsChanged(this.props.columns, nextProps.columns)) {
      return true;
    }
    return false;
  }

  componentWillReceiveProps(nextProps) {
    this.updateSize();

    if (this.shouldKeyUpdate(nextProps)) {
      this.setState({componentKey: this.state.componentKey + 1});
    }
  }

  // Add row number as first column, when we look up data
  getRow(i) {
    var row = this.props.getRow(i);
    row[this.rowNumKey] = i+1;            // 1 based row numbers
    return row;
  }

  onGridRowsUpdated({ fromRow, toRow, updated }) {
    if (fromRow !== toRow) {
      // possible if drag handle not hidden, see https://github.com/adazzle/react-data-grid/issues/822
      console.log('More than one row changed at a time in DataGrid, how?')
    }

    if(this.props.isReadOnly) {
      throw new Error("Attempting to edit cells in a read-only workflow.");
    }

    if (this.props.onEditCell)
      var colKey = Object.keys(updated)[0];
      var newVal = updated[colKey];
      this.props.onEditCell(fromRow, colKey, newVal)  // column key is also column name
  }

  onDropColumnIndexAtIndex = (fromIndex, toIndex) => {
    const sourceKey = this.props.columns[fromIndex];

    this.props.onReorderColumns(this.props.wfModuleId, {
      column: sourceKey,
      from: fromIndex,
      to: toIndex,
    });
  };

  onDragStartColumnIndex = (index) => {
    this.setState({
      draggingColumnIndex: index,
    })
  };

  onDragEnd = () => {
    this.setState({
      draggingColumnIndex: null,
    })
  };

  onRename = (renameInfo) => {
    this.props.onRenameColumn(this.props.wfModuleId, renameInfo);
  };

  render() {
    if (this.props.totalRows > 0) {
      const columns = makeFormattedCols({
        columns: this.props.columns || [],
        columnTypes: this.props.columnTypes || this.props.columns.map(_ => ''),
        showLetter: this.props.showLetter || false,
        sortColumn: this.props.sortColumn,
        sortDirection: this.props.sortDirection,
        rowNumKey: this.rowNumKey,
        onDragStartColumnIndex: this.onDragStartColumnIndex,
        onDragEnd: this.onDragEnd,
        draggingColumnIndex: this.state.draggingColumnIndex,
        onDropColumnIndexAtIndex: this.onDropColumnIndexAtIndex,
        onSortColumn: this.props.onSortColumn || (() => {}),
        onRenameColumn: this.onRename,
        isReadOnly: this.props.isReadOnly
      });

      return(
        <ReactDataGrid
          columns={columns}
          rowGetter={this.getRow}
          rowsCount={this.props.totalRows}
          minWidth={this.state.gridWidth -2}
          minHeight={this.state.gridHeight-2}   // -2 because grid has borders, don't want to expand our parent DOM node
          headerRowHeight={this.props.showLetter ? 54 : 36}
          enableCellSelect={true}
          onGridRowsUpdated={this.onGridRowsUpdated}
          key={this.state.componentKey}
          />
      )
    }  else {
      return null;
    }
  }
}
