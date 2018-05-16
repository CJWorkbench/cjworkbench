import React from 'react'
import PropTypes from 'prop-types'
import ColumnColorPicker from  './ColumnColorPicker'
import { errorText } from './errors'
import {setParamValueActionByIdName, setWfModuleStatusAction, store} from "../../workflow-reducer";
import debounce from 'lodash/debounce'
import { OutputIframeCtrl } from '../../OutputIframe'
import update from 'immutability-helper'

import chartConfig from './chartbuilder/charts/chart-type-configs'
import validateDataInput from './chartbuilder/util/validate-data-input'
import Errors from './errors'

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
      inputData: null,
    };
    this.lastWfModuleStatus = null
    this.onChangeChartSettings = this.onChangeChartSettings.bind(this);
    this.onChangeTitle = this.onChangeTitle.bind(this);
    this.onChangePrefix = this.onChangePrefix.bind(this);
    this.onChangeSuffix = this.onChangeSuffix.bind(this);
  }

  ickyDispatchSideEffect() {
    const { messages, valid } = this.state.model.errors
    if (!valid) {
      const errorMessage = messages.map(e => e.text).join('\n')
      store.dispatch(setWfModuleStatusAction(this.props.wfModuleId, 'error', errorMessage))
      this.lastWfModuleStatus = 'error'
    } else {
      if (this.lastWfModuleStatus !== 'ready') {
        store.dispatch(setWfModuleStatusAction(this.props.wfModuleId, 'ready'))
        this.lastWfModuleStatus = 'ready'
      }
    }
  }

  // Rehydrate saved chart state text into a model object that Chartbuilder can use
  loadChartProps() {
    const modelText = this.props.modelText

    let model;
    if (modelText !== "") {
      model = JSON.parse(modelText);
    } else {
      model = update(chartConfig.xy.defaultProps, {
        chartProps: {
          chartSettings: { 0: { type: { $set: this.props.type } } },
          scale: { typeSettings: { maxLength: { $set: 7 } } },
        }
      })
    }
    return model;
  }

  // Go from input data + saved model text to a Chartbuilder model, handling data parser errors if any
  parseInputData(data) {
    const model = this.loadChartProps()
    model.chartProps.input = { raw: data }

    // bypass ChartBuilder's flux et al: just use the lower-level stuff

    // this is from ChartBuilder's ChartPropertiesStore.js:
    const chartType = model.metadata.chartType
    const config = chartConfig[chartType]
    const parser = config.parser
    const chartProps = parser(config, model.chartProps)

    const errorCodes = validateDataInput(chartProps)
    const errors = errorCodes.map(ec => Errors[ec])
    const valid = errors.filter(e => e.type === 'error').length === 0

    model.errors = {
      messages: errors, // ChartBuilder should have named this "objects", not "messages"
      valid,
    }

    return model
  }

  // Retreive the data we want to chart from the server, then chart it
  loadChartState() {
    this.setState({loading: true});
    this.props.api.input(this.props.wfModuleId).then((json) => {
      const inputData = JSONtoCSV(json.rows);
      this.setState({
        loading: false,
        inputData,
        model: this.parseInputData(inputData),
      })
      this.ickyDispatchSideEffect()
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
    let newState = {value: JSON.stringify(state)};
    store.dispatch(setParamValueActionByIdName(this.props.wfModuleId, 'chart_editor', newState));
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
              Title
            </div>
            <input
              type="text"
              className="wfmoduleStringInput parameter-base t-d-gray content-2 text-field"
              value={this.state.model.metadata.title}
              onChange={this.onChangeTitle} />
          </div>
          <div >

            <div >
              <div className="label-margin t-d-gray content-3">
                Prefix
              </div>
              <input
                type="text"
                className="wfmoduleStringInput t-d-gray parameter-base content-2 text-field"
                value={this.state.model.chartProps.scale.primaryScale.prefix}
                onChange={this.onChangePrefix} />
            </div>

            <div >
              <div className="label-margin t-d-gray content-3">
                Suffix
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
