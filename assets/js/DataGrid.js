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
    return (
      <div className='rowNumber'>
          {this.props.value}
      </div>)
  }
}

RowNumberFormatter.propTypes = {
  value:    PropTypes.node.isRequired
};

var rowKey = 'row-xxxxxxxxx';  // could be a real col called row, so don't use that name


// Add row number col and make all cols resizeable
function makeFormattedCols(cols) {

  var formattedCols = [{
    key: rowKey,
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
      editable: true
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
    row[rowKey] = i+1;            // 1 based row numbers
    return row;
  }


  onGridRowsUpdated({ colKey, fromRow, toRow, updated }) {
    if (fromRow !== toRow) {
      // possible if drag handle not hidden, see https://github.com/adazzle/react-data-grid/issues/822
      console.log('More than one row changed at a time in DataGrid, should not be possible')
    }

    if (this.props.onEditCell)
      this.props.onEditCell(fromRow, colKey, updated)  // column key is also column name
  }

  render() {
    var tableData = this.props.tableData;

    // Generate the table if there's any data
    if (this.props.totalRows > 0) {

      var columns = makeFormattedCols(this.props.columns);

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
