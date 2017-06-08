// ---- TableView ----
// Displays a module's rendered output, if any

import React, { PropTypes } from 'react'
import ReactDataGrid from 'react-data-grid';

export default class TableView extends React.Component {
 
  constructor(props) {
    super(props);
  }

  render() {
    var tableData = this.props.tableData;

    // Generate the table if there's any data
    if (tableData.length > 0) {
      var columns = Object.keys(tableData[0]).map( key => { return { 'key': key, 'name': key, 'resizable':true } });
      return <ReactDataGrid
        columns={columns}
        rowGetter={ i => tableData[i] }
        rowsCount={tableData.length}
        minHeight={800} />;
    }  else {
      return null;
    }
  }
}

TableView.propTypes = {
  tableData: React.PropTypes.arrayOf(React.PropTypes.object),
};