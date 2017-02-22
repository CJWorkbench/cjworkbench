// Chart JSX component wraps a ChartBuilder

import React, { PropTypes } from 'react'
import { store, wfModuleStatusAction } from './workflow-reducer'

var ChartbuilderLocalStorageAPI = require("chartbuilder/src/js/util/ChartbuilderLocalStorageAPI");
var ChartPropertiesStore = require("chartbuilder/src/js/stores/ChartPropertiesStore");
var Chartbuilder = require("chartbuilder/src/js/components/Chartbuilder");
var ChartViewActions = require("chartbuilder/src/js/actions/ChartViewActions");

require("chartbuilder/dist/css/core.css");

// adapter, eventually obsolete with CSV format /input call, or direct edit of ChartBuilder data model
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
    var first_err= errors.messages.find(m => m.type=='error');
    if (first_err) {
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', first_err.text))
    } else {
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'ready'))
    }
  }

  // Store ChartBuilder state into our hidden text parameter, when user changes it
  // Don't store the data, that comes from input -- this suppresses parameter change when input changes)
  // Even so, this relies on test in saveState to suppress re-saving the identical content,
  // which would otherwise trigger a workflow version bump, a reload, and then another CB onChange,
  // into an infinite loop.
  saveState(model) {
    //delete model.chartProps.
    //delete model.errors;
    this.props.saveState(JSON.stringify(model));
  }

  // called when any change is made to chart. Update error status, save to hidden 'chartstate' text field
  onStateChange(model) {
    this.parseErrors(model.errors);
    this.saveState(model)
  }

  // Load our input data from render API
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

  // Load input data, settings when first rendered
  componentDidMount() {
    this.loadTable();
    var model = JSON.parse(this.props.loadState());
    ChartViewActions.updateAllChartProps(model);
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

ChartParameter.propTypes = {
		wf_module_id: React.PropTypes.number,
		revision:     React.PropTypes.number,
		saveState:    React.PropTypes.func,
		loadState:    React.PropTypes.func
}
