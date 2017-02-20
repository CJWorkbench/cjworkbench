// Chart JSX component wraps a ChartBuilder

import React from 'react'
var ChartbuilderLocalStorageAPI = require("chartbuilder/src/js/util/ChartbuilderLocalStorageAPI");
var Chartbuilder = require("chartbuilder/src/js/components/Chartbuilder");
require("chartbuilder/dist/css/core.css")

export default class ChartParameter extends React.Component {
  constructor(props) {
    super(props);
    this.loadingState = { tableData: [], loading: true };
    this.state = { tableData: [], loading: false };           // componentDidMount will trigger first load

    ChartbuilderLocalStorageAPI.defaultChart();

  }

  // Load table data from render API
  loadTable() {
    var self = this;
    var url = '/api/wfmodules/' + this.props.id + '/input';
    fetch(url)
      .then(response => response.json())
      .then(json => {
        self.setState({tableData: json, loading: false});
      }); // triggers re-render
  }

  // Load table when first rendered
  componentDidMount() {
    this.loadTable()
  }

  // If the revision changes from under us reload the table, which will trigger a setState and re-render
  componentWillReceiveProps(nextProps) {
    if (this.props.revision != nextProps.revision) {
      this.setState(this.loadingState);               // "unload" the table
      this.loadTable();
    }
  }

  // Update only when we are not loading
  shouldComponentUpdate(nextProps, nextState) {
    return !nextState.loading;
  }

  render() {
    return (<Chartbuilder
              showMobilePreview={true}
              enableJSONExport={true}
            />);
    /*      var tableData = this.state.tableData;

      if (tableData.length > 0 && !this.state.loading) {

        return (
          <h1>Hiya</h1> );

      } else {
        return false;
      }
  */
  }
}
