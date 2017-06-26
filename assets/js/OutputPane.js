// Display of output from currently selected module

import React from 'react'
import TableView from './TableView'
import PropTypes from 'prop-types'

export default class OutputPane extends React.Component {

  constructor(props) {
    super(props);
    this.state = { tableData: [], loading: false };           // componentDidMount will trigger first load
    this.loadingState = { tableData: [], loading: true };
  }

  // Load table data from render API
  loadTable(id) {
    if (id) {
      var self = this;
      var url = '/api/wfmodules/' + id + '/render';
      fetch(url, {credentials: 'include'})
        .then(response => response.json())
        .then(json => {
          self.setState(Object.assign({}, this.state, {tableData: json, loading: false}));
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
    if (this.props.id && this.state.tableData && this.state.tableData.length) {

      // console.log(JSON.stringify(this.state.tableData));

      return (
        <div className="outputpane-box">
          <div className="bg-faded outputpane-header">
            <div>
              Number of Rows: {this.state.tableData.length} 
            </div>
            <div>
              Number of Columns: {Object.keys(this.state.tableData[0]).length}      
            </div>
          </div>
          <div className="outputpane-data">
            <TableView tableData={this.state.tableData} />
          </div>
        </div>
      );
    } else if (this.props.id) {
      // When we want an output, but no TableData is present
      return (
        <div className="outputpane-box">
          <div className="bg-faded outputpane-header">
            <div>
              Number of Rows: 0 
            </div>
            <div>
              Number of Columns: 0     
            </div>
          </div>
        </div>
      );
    } else {
      return null;
    }
  }
}

OutputPane.propTypes = {
  id:       PropTypes.number,
  revision: PropTypes.number
};


