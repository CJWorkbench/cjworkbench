// ---- TableView ----
// Displays a module's rendered output, if any

import React, { PropTypes } from 'react'
import { csrfToken } from './utils'
import ReactDataGrid from 'react-data-grid';

export default class TableView extends React.Component {
  constructor(props) {
    super(props);
    this.state = { tableData: [], loading: false, isOpen: false };           // componentDidMount will trigger first load
    this.loadingState = { tableData: [], loading: true };
  }

  // Load table data from render API
  loadTable(id) {
    var self = this;
    var url = '/api/wfmodules/' + id + '/render';
    fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        self.setState(Object.assign({}, this.state, {tableData: json, loading: false}));
      }); // triggers re-render
  }

  // Load table when first rendered
  componentDidMount() {
    this.loadTable(this.props.id)
  }

  // If the revision changes from under us, or we are displaying a different output, reload the table
  componentWillReceiveProps(nextProps) {
    if (this.props.revision != nextProps.revision || this.props.id != nextProps.id) {
      this.setState(Object.assign({}, this.state, this.loadingState));               // "unload" the table
      this.loadTable(nextProps.id);
    }
  }

  // Update only when we are not loading
  shouldComponentUpdate(nextProps, nextState) {
    return !nextState.loading;
  }

  render() {
    var tableData = this.state.tableData;
    var table;

    // Generate the table if there's any data
    if (tableData.length > 0 && !this.state.loading) {
      var columns = Object.keys(tableData[0]).map( key => { return { 'key': key, 'name': key, 'resizable':true } });
      table = <ReactDataGrid
        columns={columns}
        rowGetter={ i => tableData[i] }
        rowsCount={tableData.length}
        minHeight={300} />;
    }  else {
      table = <p>(no data)</p>;
    }

    return ( <div> {table} </div> );
  }
}

TableView.propTypes = {
  id: React.PropTypes.number,
  revision: React.PropTypes.number
};