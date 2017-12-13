// ---- TableView ----
// Displays a module's rendered output, if any
// Much of the work here is ensuring that the ReactDataGrip component always fills its parent div

import React from 'react'
import ReactDOM from 'react-dom'
import ReactDataGrid from 'react-data-grid'
import PropTypes from 'prop-types'
import debounce from 'lodash/debounce'

export default class TableView extends React.Component {

  constructor(props) {
    super(props);
    this.state = { gridHeight : null };
    this.updateSize = this.updateSize.bind(this);
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

  render() {
    var tableData = this.props.tableData;

    // Generate the table if there's any data, and we've figured out our available height
    if (this.props.totalRows > 0) {

      var columns = this.props.columns.map( key => { return { 'key': key, 'name': key, 'resizable':true } });
      return <ReactDataGrid
        columns={columns}
        rowGetter={this.props.getRow}
        rowsCount={this.props.totalRows }
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
  getRow:     PropTypes.func.isRequired

};
