// Display of output from currently selected module

import React from 'react';
import TableView from './TableView'
// import { csrfToken } from './utils'

export default class OutputPane extends React.Component {

  constructor(props) {
    super(props);
    this.state = { tableData: [], loading: false };           // componentDidMount will trigger first load
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
    // Don't show anything if we don't have a selected WfModule to show

    if (this.props.id) {
      return (
        <div className="container">
          <div className="bg-faded">
            Number of rows: {this.state.tableData.length}
            <TableView tableData={this.state.tableData} />
          </div>
        </div>
      );
    } else {
      return null;
    }
  }
}

OutputPane.propTypes = {
  id: React.PropTypes.number,
  revision: React.PropTypes.number
};


