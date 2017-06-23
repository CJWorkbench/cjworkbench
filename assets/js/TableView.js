// ---- TableView ----
// Displays a module's rendered output, if any

import React from 'react'
import ReactDOM from 'react-dom'
import ReactDataGrid from 'react-data-grid';
import PropTypes from 'prop-types';

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
      this.setState({gridHeight: gridHeight});
      //console.log("updated size to " + gridHeight);
    }
  }

  componentDidMount() {
    window.addEventListener("resize", this.updateSize);
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
    if (tableData.length > 0) {

      var columns = Object.keys(tableData[0]).map( key => { return { 'key': key, 'name': key, 'resizable':true } });
      return <ReactDataGrid
        columns={columns}
        rowGetter={ i => tableData[i] }
        rowsCount={tableData.length}
        minHeight={this.state.gridHeight-2} />;   // -1 because grid has borders, don't want to expand flex grid

    }  else {
      return null;
    }
  }
}

TableView.propTypes = {
  tableData: PropTypes.arrayOf(PropTypes.object),
};