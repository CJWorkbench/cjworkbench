// ---- TableView ----
// Displays a module's rendered output, if any
// Much of the work here is ensuring that the ReactDataGrip component always fills its parent div

import React from 'react'
import ReactDOM from 'react-dom'
import ReactDataGrid from 'react-data-grid'
import PropTypes from 'prop-types'
import debounce from 'lodash/debounce'

// Custom Formatter component
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


export default class TableView extends React.Component {

  constructor(props) {
    super(props);
    this.state = { gridHeight : null };
    this.updateSize = this.updateSize.bind(this);
    this.getRow = this.getRow.bind(this);
    this.onEditCell = this.onEditCell.bind(this);
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


  onEditCell({ fromRow, toRow, updated }) {
    if (fromRow !== toRow) {
      console.log('More than one row changed at a time in TableView, should not be possible')
    }

    this.props.setRow(fromRow, updated)
  }

  render() {
    var tableData = this.props.tableData;

    // Generate the table if there's any data
    if (this.props.totalRows > 0) {

      var columns = makeFormattedCols(this.props.columns);

      return <ReactDataGrid
        columns={columns}
        rowGetter={this.getRow}
        enableCellSelect={true}
        onGridRowsUpdated={this.onEditCell}
        rowsCount={this.props.totalRows}
        minWidth={this.state.gridWidth -2}
        minHeight={this.state.gridHeight-2} />;   // -1 because grid has borders, don't want to expand flex grid

    }  else {
      return null;
    }
  }
}

TableView.propTypes = {
  totalRows:  PropTypes.number.isRequired,
  columns:    PropTypes.array.isRequired,
  getRow:     PropTypes.func.isRequired,
  setRow:     PropTypes.func.isRequired
};
