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

  idxToLetter(idx) {
    var letters = '';
    do {
      letters = String.fromCharCode(idx % 26 + 65) + letters;
      idx = Math.floor(idx / 26);
    } while(idx > 0)
    return letters;
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
          <div className='column-letter'>
            {this.idxToLetter(this.props.idx)}
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
    };
    formattedCols.push(d)
  }

  return formattedCols;
}

export default class DataGrid extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      gridHeight : 100,  // arbitrary, reset at componentDidMount, but non-zero means we get row elements in testing
      componentKey: 0   // a key for the component; updates if the column header needs
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

  onGridSort(sortCol, sortDir) {
    this.props.onSort(sortCol, sortDir);
  }

  render() {
    if (this.props.totalRows > 0) {

      this.updateRowNumKey(this.props);
      var columns = makeFormattedCols(this.props, this.rowNumKey);

      return <ReactDataGrid
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
