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


// Custom Formatter component, to render row number in a different style
export class RowNumberFormatter extends React.Component {

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


export class HeaderRenderer extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      isHovered: false,
    }
    this.handleClick = this.handleClick.bind(this);
    this.handleHoverEnter = this.handleHoverEnter.bind(this);
    this.handleHoverLeave = this.handleHoverLeave.bind(this);
  }

  handleClick() {
    this.props.onSort(this.props.colname, this.props.coltype);
  }

  handleHoverEnter() {
    this.setState({isHovered: true});
  }

  handleHoverLeave() {
    this.setState({isHovered: false});
  }

  renderSortArrow() {
    var sortDirectionClass = '';

    // If we change the sort icon, change the class names here.
    var sortDirectionDict = {
      'NONE': '',
      'ASC': 'icon-sort-up-vl-gray',
      'DESC': 'icon-sort-down-vl-gray'
    }

    if(this.props.isSorted && (this.props.sortDirection != 'NONE')) {
      // If column is sorted, set the direction to current sort direction
      sortDirectionClass = sortDirectionDict[this.props.sortDirection];
    } else if(this.state.isHovered) {
      // If there is no sort but column is hovered, set to "default" sort direction
      if(['Number', 'Date'].indexOf(this.props.coltype) >= 0) {
        sortDirectionClass = sortDirectionDict['DESC'];
      } else if(['String'].indexOf(this.props.coltype) >= 0) {
        sortDirectionClass = sortDirectionDict['ASC'];
      }
    }

    if(sortDirectionClass.length > 0) {
      return (
          <div className='column-sort-arrow'>
            <div className={sortDirectionClass}></div>
          </div>
      );
    }
    return '';
  }

  renderLetter() {
    if(this.props.showLetter) {
      return (
          // The 'column-letter' class name is used in the test so please be careful with it
          <div className='column-letter'>
            {idxToLetter(this.props.idx)}
          </div>
      );
    }
    return '';
  }

  render() {
    let sortArrowSection = this.renderSortArrow();
    let letterSection = this.renderLetter();

    return (
        <div
            onClick={this.handleClick}
            onMouseEnter={this.handleHoverEnter}
            onMouseLeave={this.handleHoverLeave}
            style={this.state.isHovered ? {backgroundColor:'#219EE8'} : undefined}
        >
            {letterSection}
            <div className="sort-container">
                {this.props.colname}
                {sortArrowSection}
            </div>
        </div>
    );
  }
}


// Add row number col and make all cols resizeable
function makeFormattedCols(props, rowNumKey) {
  var cols = props.columns;
  var editable = (props.onEditCell !== undefined);
  var coltypes = props.columnTypes;

  // Add a row number column, which has its own formatting
  var formattedCols = [{
    key: rowNumKey,
    name: '',
    formatter: RowNumberFormatter,
    width: 40,
    locked: true,
  }];

  for (let idx in cols) {
    let currentHeaderRenderer = (
        <HeaderRenderer
            colname={cols[idx]}
            coltype={coltypes ? coltypes[idx] : ''}
            isSorted={props.sortColumn == cols[idx]}
            sortDirection={props.sortDirection}
            idx={idx}
            onSort={props.onSortColumn}
            showLetter={props.showLetter}
        />
    );
    let d = {
      key: cols[idx],
      name: cols[idx],
      resizable: true,
      editable: editable,
      width: 160,
      headerRenderer: currentHeaderRenderer,
        draggable: true
    };
    formattedCols.push(d)
  }

  return formattedCols;
}


// To weave a function through react-data-grid's innards...:
//
// 1. Create a function in DataGrid and supply it in a Provider
// 2. Wrap HeaderCell in DraggableHeaderCell, which passes its `props.inner` as
//    HeaderCell's `props`
// 3. Wrap DraggableHeaderCell in a Consumer, to read `props.onDragDropHeader`

// This import is only so we can mock for tests. It should be a React.createContext()
// one-liner.
import DropFunctionContext from './DataGridDragDropContext'
// (When we upgrade to enzyme-adapter-react-16>1.1.1, nix this:)
//const DropFunctionContext = React.createContext(() => {})


class DraggableHeaderCell extends HeaderCell {
  constructor(props) {
    super(props)

    this.normalStyle = { width: 0, cursor: 'move', opacity: 1 }
    this.draggingStyle = { width: 0, cursor: 'move', opacity: 0.2 }
    this.normalClassName = ''
    this.droppingClassName = 'rdg-can-drop'

    this.state = {
      // These styles and classNames are copied from react-data-grid-addons
      style: this.normalStyle, // "am I dragging?"
      className: this.normalClassName, // "am I dropping?"
    }
  }

  onDragStart = (ev) => {
    ev.dataTransfer.setData('application/json', JSON.stringify({
      type: 'DraggableHeaderCell',
      columnKey: this.props.innerProps.column.key,
    }))
    ev.dataTransfer.effectAllowed = [ 'move' ]
    ev.dataTransfer.dropEffect = 'move'

    this.props.onDragStartHeader(this.props.innerProps.column.key)

    this.setState({
      style: this.draggingStyle,
    })
  }

  onDragEnter = (ev) => {
    if (!this.canDrop()) return

    this.setState({
      className: this.droppingClassName,
    })
  }

  onDragLeave = (ev) => {
    if (!this.canDrop()) return

    this.setState({
      className: this.normalClassName,
    })
  }

  onDragEnd = () => {
    this.props.onDragEndHeader()
    this.setState({
      style: this.normalStyle,
      className: this.normalClassName,
    })
  }

  canDrop() {
    return !!this.props.draggingColumnKey && this.props.draggingColumnKey !== this.props.innerProps.column.key
  }

  onDragOver = (ev) => {
    if (!this.canDrop()) return

    ev.preventDefault() // default is, "can't drop"
  }

  onDrop = (ev) => {
    if (!this.canDrop()) return

    ev.preventDefault() // we want no browser defaults

    this.props.onDragDropHeader(this.props.draggingColumnKey, this.props.innerProps.column.key)
    this.props.onDragEndHeader()

    this.setState({
      style: this.normalStyle,
      className: this.normalClassName,
    })
  }

  render() {
    return (
      <div
        className={this.state.className}
        style={this.state.style}
        draggable="true"
        onDragStart={this.onDragStart}
        onDragEnter={this.onDragEnter}
        onDragLeave={this.onDragLeave}
        onDragEnd={this.onDragEnd}
        onDragOver={this.onDragOver}
        onDrop={this.onDrop}
        >
        <HeaderCell {...this.props.innerProps} />
      </div>
    )
  }
}

class ConnectedDraggableHeaderCell extends React.Component {
  render() {
    return (
      <DropFunctionContext.Consumer>
        { value =>
          <DraggableHeaderCell innerProps={this.props} {...value} />
        }
      </DropFunctionContext.Consumer>
    )
  }
}


export default class DataGrid extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      gridHeight : 100,  // arbitrary, reset at componentDidMount, but non-zero means we get row elements in testing
      componentKey: 0,  // a key for the component; updates if the column header needs
      dropContextValue: {
        // not mutable
        onDragDropHeader: this.onDragDropHeader,
        onDragStartHeader: this.onDragStartHeader,
        onDragEndHeader: this.onDragEndHeader,
        draggingColumnKey: null, // not ev.dataTransfer.setData(), because that's only visible in onDrop()
      },
    };
    this.rowNumKey = null;  // can't be in state because we need to update it in render() for getRow() to use

    this.updateSize = this.updateSize.bind(this);
    // this.updateRowNumKey= this.updateRowNumKey.bind(this);
    this.getRow = this.getRow.bind(this);
    this.onGridRowsUpdated = this.onGridRowsUpdated.bind(this);
    this.onGridSort = this.onGridSort.bind(this);

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
  updateRowNumKey(props) {
    var rowNumKey = 'rn_';
    while (props.columns.includes(rowNumKey)) {
      rowNumKey += '_';
    }
    this.rowNumKey = rowNumKey;
  }

  componentDidMount() {
    window.addEventListener("resize", debounce(this.updateSize, 200));
    this.updateSize();
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

    if(this.shouldKeyUpdate(nextProps)) {
      this.setState({componentKey: this.state.componentKey + 1});
    }
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.updateSize);
  }
/*
  // don't re-render while we are being dragged. makes things very smooth.
  shouldComponentUpdate(nextProps) {
    return !nextProps.resizing;
  }
*/
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

    if (this.props.onEditCell)
      var colKey = Object.keys(updated)[0];
      var newVal = updated[colKey];
      this.props.onEditCell(fromRow, colKey, newVal)  // column key is also column name
  }

  onGridSort(sortCol, sortDir) {
    this.props.onSort(sortCol, sortDir);
  }

  onDragDropHeader = (sourceKey, targetKey) => {
    const sourceIdx = this.props.columns.indexOf(sourceKey)
    const targetIdx = this.props.columns.indexOf(targetKey)

    if (sourceIdx === -1 || targetIdx === -1) {
      throw new Error(`Invalid columns in drag+drop: from ${sourceKey} (${sourceIdx}) to ${targetKey} (${targetIdx})`)
    }

    this.props.reorderColumns(this.props.selectedModule, {
      column: sourceKey,
      from: sourceIdx,
      to: targetIdx
    });
  }

  onDragStartHeader = (column) => {
    if (this.state.dropContextValue.draggingColumnKey === column) return

    this.setState({
      dropContextValue: { ...this.state.dropContextValue, draggingColumnKey: column },
    })
  }

  onDragEndHeader = () => {
    if (this.state.dropContextValue.draggingColumnKey === null) return

    this.setState({
      dropContextValue: { ...this.state.dropContextValue, draggingColumnKey: null },
    })
  }

  render() {
    //console.log(this.props);

    if (this.props.totalRows > 0) {

      this.updateRowNumKey(this.props);
      var columns = makeFormattedCols(this.props, this.rowNumKey);
      //console.log(columns)

      return(
        <DropFunctionContext.Provider value={this.state.dropContextValue}>
          <ReactDataGrid
            columns={columns}
            rowGetter={this.getRow}
            rowsCount={this.props.totalRows}
            minWidth={this.state.gridWidth -2}
            minHeight={this.state.gridHeight-2}   // -2 because grid has borders, don't want to expand our parent DOM node
            headerRowHeight={this.props.showLetter ? 54 : 36}
            enableCellSelect={true}
            onGridRowsUpdated={this.onGridRowsUpdated}
            enableDragAndDrop={true}
            draggableHeaderCell={ConnectedDraggableHeaderCell}
            key={this.state.componentKey}
            />
        </DropFunctionContext.Provider>
      )
    }  else {
      return null;
    }
  }
}

DataGrid.propTypes = {
  totalRows:  PropTypes.number.isRequired,
  columns:    PropTypes.array.isRequired,
  getRow:     PropTypes.func.isRequired,
  resizing:   PropTypes.bool,
  onEditCell: PropTypes.func
};
