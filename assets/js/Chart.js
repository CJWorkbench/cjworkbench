// Chart JSX component wraps a ChartBuilder

import React from 'react'
import { store, wfModuleStatusAction } from './workflow-reducer'

var ChartbuilderLocalStorageAPI = require("chartbuilder/src/js/util/ChartbuilderLocalStorageAPI");
var ChartPropertiesStore = require("chartbuilder/src/js/stores/ChartPropertiesStore");
var Chartbuilder = require("chartbuilder/src/js/components/Chartbuilder");
var ChartViewActions = require("chartbuilder/src/js/actions/ChartViewActions");

require("chartbuilder/dist/css/core.css");

// adapter, eventually obsolete with CSV format /input call, or better ChartBuilder integration
function JSONtoCSV(d) {
  if (d && d.length > 0) {
    var colnames = Object.keys(d[0]).filter(key => key != 'index');
    var text = colnames.join(',') + '\n';
    for (var row of d) {
      text += colnames.map(name => row[name]).join(',') + '\n';
    }
    return text;

  } else {

    return '';

  }
}

export default class ChartParameter extends React.Component {
  constructor(props) {
    super(props);
    this.loadingState = { loading: true };
    this.state = { loading: false }; // componentDidMount will trigger first load

    this.onStateChange = this.onStateChange.bind(this);

    ChartbuilderLocalStorageAPI.defaultChart();
  }

  setError(message) {

  }

  // Turn ChartBuilder errors into module errors (so user gets the red light etc.)
  parseErrors(errors) {
    var errs = errors.messages.filter(m => m.type=='error');
    if (errs.length>0) {
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', errs[0].text))
    } else {
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'ready'))
    }
  }

  // called when any change is made to chart
  onStateChange(model) {
    this.parseErrors(model.errors);
  }

  // Load table data from render API
  loadTable() {
    this.setState(this.loadingState);
    var self = this;
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    fetch(url)
      .then(response => response.json())
      .then(json => {

        var csv_text = JSONtoCSV(json);
        var input = Object.assign( {}, ChartPropertiesStore.getAll(), { raw: csv_text, type: undefined } );
        ChartViewActions.updateInput("input", input);
        this.setState({loading: false})

      });
  }

  // Load table when first rendered
  componentDidMount() {
    this.loadTable()
  }

  // If the revision changes from under us reload the table, which will trigger a setState and re-render
  componentWillReceiveProps(nextProps) {
    if (this.props.revision != nextProps.revision) {
      this.loadTable();
    }
  }

  // Update only when we are not loading
  shouldComponentUpdate(nextProps, nextState) {
    return !nextState.loading;
  }

  render() {
    return (<Chartbuilder autosave={true} onStateChange={this.onStateChange}/>);
  }
}
