import React from 'react'
import ColumnColorPicker from  './ColumnColorPicker'
import debounce from 'lodash/debounce'
import DateScaleSettings from './DateScaleSettings'

/* Flux stores */
var RendererWrapper = require("chartbuilder/src/js/components/RendererWrapper");
var ChartServerActions = require("chartbuilder/src/js/actions/ChartServerActions");
var ChartPropertiesStore = require("chartbuilder/src/js/stores/ChartPropertiesStore");
var ChartMetadataStore = require("chartbuilder/src/js/stores/ChartMetadataStore");
var SessionStore = require("chartbuilder/src/js/stores/SessionStore");
var ErrorStore = require("chartbuilder/src/js/stores/ErrorStore");

export default class ChartEditor extends React.Component {
  constructor(props) {
    super(props);
    this.state = this.getStateFromStores();
    this.onChangeChartSettings = this.onChangeChartSettings.bind(this);
    this.onChangeTitle = this.onChangeTitle.bind(this);
    this.saveState = this.saveState.bind(this);
    this.onStateChange = this.onStateChange.bind(this);
    this.onErrorsChange = this.onErrorsChange.bind(this);
    this.onChangeDate = this.onChangeDate.bind(this);
    this.onChangePrefix = this.onChangePrefix.bind(this);
    this.onChangeSuffix = this.onChangeSuffix.bind(this);
    this.getStateFromStores = this.getStateFromStores.bind(this);
  }

  getStateFromStores() {
  	return {
  		chartProps: ChartPropertiesStore.getAll(),
  		metadata: ChartMetadataStore.getAll(),
  		session: SessionStore.getAll()
  	};
  }

  onErrorsChange() {
    this.setState({errors: ErrorStore.getAll()})
  }

  saveState(model) {
    ChartServerActions.receiveModel(model);
  }

  onStateChange() {
    this.setState(this.getStateFromStores());
  }

  componentDidMount() {
    ChartPropertiesStore.addChangeListener(this.onStateChange);
    ChartMetadataStore.addChangeListener(this.onStateChange);
    ErrorStore.addChangeListener(this.onErrorsChange);
    SessionStore.addChangeListener(this.onStateChange);
  }

  componentWillUnmount() {
		ChartPropertiesStore.removeChangeListener(this.onStateChange);
		ChartMetadataStore.removeChangeListener(this.onStateChange);
		ErrorStore.removeChangeListener(this.onErrorsChange);
		SessionStore.removeChangeListener(this.onStateChange);
	}

  onChangeChartSettings(state) {
    let stateCopy = JSON.parse(JSON.stringify(this.state));
    stateCopy.chartProps.chartSettings = state;
    this.saveState(stateCopy);
  }

  onChangeTitle(e) {
    let stateCopy = JSON.parse(JSON.stringify(this.state));
    stateCopy.metadata.title = e.target.value;
    this.saveState(stateCopy);
  }

  onChangePrefix(e) {
    let stateCopy = JSON.parse(JSON.stringify(this.state));
    stateCopy.chartProps.scale.primaryScale.prefix = e.target.value;
    this.saveState(stateCopy);
  }

  onChangeSuffix(e) {
    let stateCopy = JSON.parse(JSON.stringify(this.state));
    stateCopy.chartProps.scale.primaryScale.suffix = e.target.value;
    this.saveState(stateCopy);
  }

  onChangeDate(uh) {
    let stateCopy = JSON.parse(JSON.stringify(this.state));
    stateCopy.chartProps.scale = uh;
    this.saveState(stateCopy);
  }

  render() {
    if (this.state.errors && this.state.errors.valid) {
      return (
        <div>
          <div className="param-line-margin">
            <ColumnColorPicker
              series={this.state.chartProps.chartSettings}
              saveState={this.onChangeChartSettings}/>
          </div>
          <div className="param-line-margin">
            <div className="label-margin t-d-gray content-3">
              Chart Title
            </div>
            <input
              type="text"
              className="wfmoduleStringInput parameter-base t-d-gray content-2 text-field"
              value={this.state.metadata.title}
              onChange={this.onChangeTitle} />
          </div>
          <div className="paramX-line-margin">

            <div className="param2-line-margin">
              <div className="label-margin t-d-gray content-3">
                Axis prefix
              </div>
              <input
                type="text"
                className="wfmoduleStringInput t-d-gray parameter-base content-2 text-field"
                value={this.state.chartProps.scale.primaryScale.prefix}
                onChange={this.onChangePrefix} />
            </div>

            <div className="param2-line-margin">
              <div className="label-margin t-d-gray content-3">
                Axis suffix
              </div>
              <input
                type="text"
                className="wfmoduleStringInput t-d-gray parameter-base content-2 text-field"
                value={this.state.chartProps.scale.primaryScale.suffix}
                onChange={this.onChangeSuffix} />
            </div>

          </div>

          {this.state.chartProps.scale.hasDate &&
          <DateScaleSettings
            scale={this.state.chartProps.scale}
            nowOffset={this.state.session.nowOffset}
            now={this.state.session.now}
            onUpdate={this.onChangeDate}/>
          }
        </div>
      )
    } else {
      return (
        <div></div>
      )
    }
  }
}
