// Display of output from currently selected module

import React from 'react'
import TableView from './TableView'
import PropTypes from 'prop-types'

export default class OutputPane extends React.Component {

  constructor(props) {
    super(props);
    this.state = { tableData: {}, loading: false };           // componentDidMount will trigger first load
    this.loadingState = { tableData: [], loading: true };
  }

  // Load table data from render API
  loadTable(id) {
    if (id) {
      var self = this;
      this.props.api.render(id)
        .then(json => {
          self.setState({tableData: json, loading: false});
        }); // triggers re-render
    }
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
    if (!this.props.id) {
      return null
    }

    // Make a table component if we have the data
    var tableView = null;
    var nrows = 0;
    var ncols = 0;
    if (this.state.tableData && this.state.tableData.totalrows>0) {
      tableView =
        <div className="outputpane-data">
          <TableView tableData={this.state.tableData} />
        </div>
      nrows = this.state.tableData.totalrows;
      ncols = this.state.tableData.columns.length;
    }

    return (
      <div className="outputpane-box">
        <div className="outputpane-header d-flex flex-row justify-content-start">
          <div className='d-flex flex-column align-items-center justify-content-center mr-5'>
            <div className='content-4 t-m-gray mb-2'>Rows</div>
            <div className='content-2 t-d-gray'>{nrows}</div>
          </div>
          <div className='d-flex flex-column align-items-center justify-content-center'>
            <div className='content-4 t-m-gray mb-2'>Columns</div>
            <div className='content-2 t-d-gray'>{ncols}</div>
          </div>
        </div>
        {tableView}
      </div>
    );
  }
}

OutputPane.propTypes = {
  id:       PropTypes.number,
  revision: PropTypes.number,
  api:      PropTypes.object.isRequired
};


