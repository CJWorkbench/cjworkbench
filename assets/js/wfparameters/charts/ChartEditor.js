import React from 'react'
import PropTypes from 'prop-types'
import ColumnColorPicker from  './ColumnColorPicker'
import DateScaleSettings from './DateScaleSettings'
import { errorText } from './errors'
import {changeParamAction, wfModuleStatusAction, store} from "../../workflow-reducer";
import debounce from 'lodash/debounce'
import { OutputIframeCtrl } from '../../OutputIframe'

// Chartbuilder Flux stores. These are global but we only uses them synchronously to put data in, parse it, get CB state out
var ChartServerActions = require("chartbuilder/src/js/actions/ChartServerActions");
var ChartPropertiesStore = require("chartbuilder/src/js/stores/ChartPropertiesStore");
var ChartMetadataStore = require("chartbuilder/src/js/stores/ChartMetadataStore");
var SessionStore = require("chartbuilder/src/js/stores/SessionStore");
var ErrorStore = require("chartbuilder/src/js/stores/ErrorStore");

var ChartViewActions = require("chartbuilder/src/js/actions/ChartViewActions");
var chartConfig = require("chartbuilder/src/js/charts/chart-type-configs");

// Overload the chartbuilder error messages so we can set our own
var cbErrorText = require("chartbuilder/src/js/util/error-names");
Object.keys(cbErrorText).map( (key) => {
  cbErrorText[key].text = errorText[key].text;
});

// Data format adapter, would eventually be obsolete with a CSV format /input endpoint
function JSONtoCSV(d) {
  if (d && d.length > 0) {
    var colnames = Object.keys(d[0]).filter(key => key != 'index');
    var text = colnames.join(',') + '\n';
    for (var row of d) {
      text += colnames.map((name) => {return "\"" + row[name] + "\""}).join(',') + '\n';
    }
    return text;
  } else {
    return '';
  }
}


export default class ChartEditor extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      loading: true,
      model: null,      // Chartbuilder model object. Also where we store/update current parameter values
      inputData: null
    };
    this.onChangeChartSettings = this.onChangeChartSettings.bind(this);
    this.onChangeTitle = this.onChangeTitle.bind(this);
    this.onChangeDate = this.onChangeDate.bind(this);
    this.onChangePrefix = this.onChangePrefix.bind(this);
    this.onChangeSuffix = this.onChangeSuffix.bind(this);
    this.getStateFromStores = this.getStateFromStores.bind(this);
    this.saveStateToDatabase = debounce(this.saveStateToDatabase, 1000);
  }

   // Turn ChartBuilder errors into module errors (so user gets the red light etc.)
  parseErrors(errors) {
    var errorMessage = errors.messages
      .filter((m) => {
        return m.type === 'error';
      })
      .map((m) => {
        return m.text;
      })
      .join("\n\r");
    if (errorMessage !== '') {
      store.dispatch(wfModuleStatusAction(this.props.wfModuleId, 'error', errorMessage))
    } else {
      store.dispatch(wfModuleStatusAction(this.props.wfModuleId, 'ready'))
    }
  }

  // Rehydrate saved chart state text into a model object that Chartbuilder can use
  loadChartProps(modelText, data) {
    let model;
    if (modelText !== "") {
      model = JSON.parse(modelText);
    } else {
      let defaults = chartConfig.xy.defaultProps;
      defaults.chartProps.chartSettings[0].type = this.props.type;
      defaults.chartProps.scale.typeSettings.maxLength = 7;
      model = defaults;
    }
    model.chartProps.input = {raw: data};
    return model;
  }

  // Retrieve Chartbuilder's current state from its global store
  getStateFromStores() {
  	return {
  		chartProps: ChartPropertiesStore.getAll(),
  		metadata: ChartMetadataStore.getAll(),
  		session: SessionStore.getAll(),
      errors: ErrorStore.getAll()
  	};
  }

  // Go from input data + saved model text to a Chartbuilder model, handling data parser errors if any
  parseChartState(data) {
    let newModel = this.loadChartProps(this.props.modelText, data);
    let parsedModel;
    // In order to preserve the saved chart settings, we have to set up the initial chart model with the raw input data.
    // However, if there are errors in the data, receiveModel won't find them. We need to call .updateInput so Chartbuilder's
    // internal parser will find errors in the data.
    ChartServerActions.receiveModel(newModel);
    ChartViewActions.updateInput('input', {raw: data});
    parsedModel = this.getStateFromStores();
    if (parsedModel.errors.valid === false) {
        this.parseErrors(parsedModel.errors);
        return null;
    }
    return parsedModel;
  }

  // Retreive the data we want to chart from the server, then chart it
  loadChartState() {
    this.setState({loading: true});
    this.props.api.input(this.props.wfModuleId).then((json) => {
      let inputData = JSONtoCSV(json.rows);
      let parsedChartState = this.parseChartState(inputData);
      this.setState({model: parsedChartState, inputData, loading: false});
    })
  }

  // When the model state changes (when a parameter is changed) the chart needs to update, and we need to store to the server
  saveState(state) {
    if (OutputIframeCtrl) {
      OutputIframeCtrl.postMessage({model: state}, '*');
    }
    this.saveStateToDatabase(state);
  }

  // Push new state to server, sans the data we are charting (which comes from the previous module)
  saveStateToDatabase(state) {
    // Make a copy so we can remove the inpit data
    let stateCopy = this.deepCopyState(state);
    Object.assign(stateCopy.chartProps, {data: undefined, input: undefined});
    let newStateString = JSON.stringify(state);
    store.dispatch(changeParamAction(this.props.wfModuleId, 'chart_editor', newStateString));
  }

  deepCopyState(state) {
    return JSON.parse(JSON.stringify(state));
  }

  componentDidMount() {
    this.loadChartState();
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.revision !== this.props.revision) {
      this.loadChartState();
    }
  }

  // Callbacks to handle parameter changes. Some components are controlled input fields.
  // All parameters must both setState on this component so that we get a re-render with new settings,
  // and saveState so that the chart re-renders and we save the change to the server.

  onChangeChartSettings(state) {
    let stateCopy = this.deepCopyState(this.state.model);
    stateCopy.chartProps.chartSettings = state;
    this.setState({model: stateCopy});
    this.saveState(stateCopy);
  }

  onChangeTitle(e) {
    let stateCopy = this.deepCopyState(this.state.model);
    stateCopy.metadata.title = e.target.value;
    this.setState({model: stateCopy});
    this.saveState(stateCopy);
  }

  onChangePrefix(e) {
    let stateCopy = this.deepCopyState(this.state.model);
    stateCopy.chartProps.scale.primaryScale.prefix = e.target.value;
    this.setState({model: stateCopy});
    this.saveState(stateCopy);
  }

  onChangeSuffix(e) {
    let stateCopy = this.deepCopyState(this.state.model);
    stateCopy.chartProps.scale.primaryScale.suffix = e.target.value;
    this.setState({model: stateCopy});
    this.saveState(stateCopy);
  }

  onChangeDate(uh) {
    let stateCopy = this.deepCopyState(this.state.model);
    stateCopy.chartProps.scale = uh;
    this.setState({model: stateCopy});
    this.saveState(stateCopy);
  }

  render() {
    if (this.state.model && this.state.model.errors && this.state.model.errors.valid) {
      return (
        <div>
          <div>
            <ColumnColorPicker
              series={this.state.model.chartProps.chartSettings}
              saveState={this.onChangeChartSettings}/>
          </div>
          <div className="param-line-margin">
            <div className="label-margin t-d-gray content-3">
              Chart Title
            </div>
            <input
              type="text"
              className="wfmoduleStringInput parameter-base t-d-gray content-2 text-field"
              value={this.state.model.metadata.title}
              onChange={this.onChangeTitle} />
          </div>
          <div className="param-line-margin">

            <div className="param2-line-margin">
              <div className="label-margin t-d-gray content-3">
                Axis prefix
              </div>
              <input
                type="text"
                className="wfmoduleStringInput t-d-gray parameter-base content-2 text-field"
                value={this.state.model.chartProps.scale.primaryScale.prefix}
                onChange={this.onChangePrefix} />
            </div>

            <div className="param2-line-margin">
              <div className="label-margin t-d-gray content-3">
                Axis suffix
              </div>
              <input
                type="text"
                className="wfmoduleStringInput t-d-gray parameter-base content-2 text-field"
                value={this.state.model.chartProps.scale.primaryScale.suffix}
                onChange={this.onChangeSuffix} />
            </div>

          </div>

        </div>
      )
    } else {
      return (
        <div></div>
      )
    }
  }
}

ChartEditor.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  revision:   PropTypes.number.isRequired,
  wfModuleId: PropTypes.number.isRequired,
  modelText:  PropTypes.string.isRequired,
  type:       PropTypes.string.isRequired,
  api:        PropTypes.object.isRequired
};
