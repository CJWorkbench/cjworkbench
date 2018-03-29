// ---- DataGrid  ----
// Core table display component.
// Contains all logic that interfaces with react-data-grid
// Paged loading and other logic is in TableView, which is typically our parent

import React from 'react'
import ReactDOM from 'react-dom'
import ReactDataGrid from 'react-data-grid'
import PropTypes from 'prop-types'
import debounce from 'lodash/debounce'

// Custom Formatter component, to render row number in a different style
class RowNumberFormatter extends React.Component {

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

// Add row number col and make all cols resizeable
function makeFormattedCols(cols, rowNumKey, editable) {

  // Add a row number column, which has its own formatting
  var formattedCols = [{
    key: rowNumKey,
    name: '',
    formatter: RowNumberFormatter,
    width: 40,
    locked: true
  }];

  for (let idx in cols) {
    let d = {
      key: cols[idx],
      name: cols[idx],
      resizable: true,
      editable: editable
    };
    formattedCols.push(d)
  }

  return formattedCols;
}


export default class DataGrid extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      gridHeight : 100  // arbitrary, reset at componentDidMount, but non-zero means we get row elements in testing
    };
    this.rowNumKey = null;  // can't be in state because we need to update it in render() for getRow() to use

    this.updateSize = this.updateSize.bind(this);
    // this.updateRowNumKey= this.updateRowNumKey.bind(this);
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

  componentWillReceiveProps(nextProps) {
    this.updateSize();
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.updateSize);
  }

  // don't re-render while we are being dragged. makes things very smooth.
  shouldComponentUpdate(nextProps) {
    return !nextProps.resizing;
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

    if (this.props.onEditCell)
      var colKey = Object.keys(updated)[0];
      var newVal = updated[colKey];
      this.props.onEditCell(fromRow, colKey, newVal)  // column key is also column name
  }

  render() {
    var tableData = this.props.tableData;

    // Generate the table if there's any data
    if (this.props.totalRows > 0) {

      this.updateRowNumKey(this.props);
      var columns = makeFormattedCols(this.props.columns, this.rowNumKey, this.props.onEditCell !== undefined);

      return <ReactDataGrid
        columns={columns}
        rowGetter={this.getRow}
        rowsCount={this.props.totalRows}
        minWidth={this.state.gridWidth -2}
        minHeight={this.state.gridHeight-2}   // -2 because grid has borders, don't want to expand our parent DOM node
        enableCellSelect={true}
        onGridRowsUpdated={this.onGridRowsUpdated} />

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
