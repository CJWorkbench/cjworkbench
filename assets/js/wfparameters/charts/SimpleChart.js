// Chart JSX component wraps a ChartBuilder

import React from 'react'
import { store, wfModuleStatusAction } from '../../workflow-reducer'
import PropTypes from 'prop-types'
import { errorText } from './errors'
import debounce from 'lodash/debounce'

var ChartViewActions = require("chartbuilder/src/js/actions/ChartViewActions");
var chartConfig = require("chartbuilder/src/js/charts/chart-type-configs");
var saveSvgAsPng = require("save-svg-as-png");

/* Flux stores */
var RendererWrapper = require("chartbuilder/src/js/components/RendererWrapper");
var ChartServerActions = require("chartbuilder/src/js/actions/ChartServerActions");
var ChartPropertiesStore = require("chartbuilder/src/js/stores/ChartPropertiesStore");
var ChartMetadataStore = require("chartbuilder/src/js/stores/ChartMetadataStore");
var SessionStore = require("chartbuilder/src/js/stores/SessionStore");
var ErrorStore = require("chartbuilder/src/js/stores/ErrorStore");

require("../../../css/chartbuilder_fonts_colors.css")
require("../../../css/chartbuilder.css");

// Overload the chartbuilder error messages so we can set our own
var cbErrorText = require("chartbuilder/src/js/util/error-names");
Object.keys(cbErrorText).map( (key) => {
  cbErrorText[key].text = errorText[key].text;
});

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

export default class SimpleChartParameter extends React.Component {

  constructor(props) {
    super(props);
    this.state = { loading: true, loaded_ever: false };
    this.saveChartProps = debounce(this.props.saveState, 500);
    this.loadingState = { loading: true, loaded_ever: true };
    this.onStateChange = this.onStateChange.bind(this);
    this.saveImage = this.saveImage.bind(this);
    this.parseErrors = this.parseErrors.bind(this);
    this.onErrorChange = this.onErrorChange.bind(this);
    this.loadChartProps = this.loadChartProps.bind(this);
    // I kinda hate this... we store the last chart state we were given here, to suppress unnecessary API calls.
    // We can't put it in React state because we don't want to trigger a render... and this state doesn't change
    // the render, as this value is passed to us by the ChartBuilder component, so it's already rendered.
    // Only tricky bit is to remember to reset this when our props change.
    this.lastChartStateString = null;
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
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', errorMessage))
    } else {
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'ready'))
    }
  }

  // Store ChartBuilder state and PNG image into our hidden parameters
  saveState(model) {
    // Store chart parameters. Don't store chart data, that comes from input
    var model2 = JSON.parse(JSON.stringify(model)); // don't alter real model!
    model2.chartProps = Object.assign({}, model2.chartProps,
      {data: undefined, input: undefined});
    var stateString = JSON.stringify(model2);

    // Save to server only if there is something to save
    if (stateString !== this.lastChartStateString) {
      // console.log("saving chart state");
      this.saveChartProps(stateString);
      this.lastChartStateString = stateString;
    }
  }

  // Store most recently rendered chart image
  saveImage() {
    var el = document.getElementsByClassName('renderer-svg-desktop')[0];
    if (el) {
      var chartNode = el.getElementsByClassName('chartbuilder-svg')[0]

      if (chartNode) {
        saveSvgAsPng.svgAsPngUri(chartNode, {}, dataURI => {
          this.props.saveImageDataURI(dataURI)
        })
      }
    }
  }

  // called when any change is made to chart. Update error status, save to hidden 'chartstate' text field
  onStateChange(errors) {
    var model = this.getStateFromStores();
    if (this.state && this.state.loaded_ever && !this.state.loading) {
      this.setState(Object.assign({}, model, {errors: errors || this.state.errors}));
      this.saveState(model);
      if (errors) {
        this.parseErrors(errors);
      }
    }
  }

  // called when errors return -- they need to be handled seperately
  onErrorChange() {
    this.setState({loading: false});
    var errors = ErrorStore.getAll();
    this.onStateChange(errors);
  }

  getStateFromStores() {
    // Don't get errors here. Errors default to 'valid' before input
    // has processed, so instead we wait until the first time we add
    // input data to the store.
  	return {
  		chartProps: ChartPropertiesStore.getAll(),
  		metadata: ChartMetadataStore.getAll(),
  		session: SessionStore.getAll()
  	};
  }

  // Load our input data from render API, restore start state from hidden param
  loadChart() {
    this.setState(this.loadingState);
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    return fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        return { raw: JSONtoCSV(json.rows) };
      });
  }

  loadChartProps(modelText) {
    var model;
    var defaults = chartConfig.xy.defaultProps;
    if (modelText !== "") {
      model = JSON.parse(modelText);
      this.lastChartStateString = modelText;
    } else {
      model = defaults;
    }
    model.chartProps.input = {raw: ''} //blank data to start
    return model;
  }

  componentWillMount(props) {
    var defaults = chartConfig.xy.defaultProps;
    var modelText = this.props.loadState();
    var newModel = this.loadChartProps(modelText);
    defaults.chartProps.chartSettings[0].type = this.props.chartType || 'line';
    defaults.chartProps.scale.typeSettings.maxLength = 7;
    ChartServerActions.receiveModel(newModel);
  }

  // Load input data, settings when first rendered
  componentDidMount() {
    ChartPropertiesStore.addChangeListener(this.onStateChange);
    ChartMetadataStore.addChangeListener(this.onStateChange);
    ErrorStore.addChangeListener(this.onErrorChange);
    SessionStore.addChangeListener(this.onStateChange);
    this.loadChart().then(result => {
      this.setState({loading: false});
      ChartViewActions.updateInput('input', result);
    });
  }

  componentWillUnmount() {
		ChartPropertiesStore.removeChangeListener(this.onStateChange);
		ChartMetadataStore.removeChangeListener(this.onStateChange);
		ErrorStore.removeChangeListener(this.onErrorChange);
		SessionStore.removeChangeListener(this.onStateChange);
	}

  // If the revision changes from under us reload the table, which will trigger a setState and re-render
  componentWillReceiveProps(nextProps) {
    var modelText;
    var model;
    if (this.props.revision !== nextProps.revision) {
      this.loadChart().then((result) => {
        ChartViewActions.updateInput('input', result);
        modelText = this.props.loadState();
        if (this.lastChartStateString !== modelText) {
          model = this.loadChartProps(modelText);
          model.chartProps.input = this.state.chartProps.input;
          ChartServerActions.receiveModel(model);
        }
      });
    }
  }

  // Update only when we are not loading
  shouldComponentUpdate(nextProps, nextState) {
    if (typeof nextState.errors === 'undefined') {
      return false;
    }
    return !nextState.loading;
  }

  render() {
    if (!this.state.loading &&
      (typeof this.state.errors !== 'undefined' &&
      this.state.errors.valid)) {
      return (
        <RendererWrapper
          editable={true}
          showMetadata={true}
          model={this.state}
          enableResponsive={true}
          className="render-svg-mobile"
          svgClassName={this.props.renderedSVGClassName} />
      )
    } else {
      return <div></div>;
    }
  }
}

SimpleChartParameter.propTypes = {
		wf_module_id:     PropTypes.number,
		revision:         PropTypes.number,
		saveState:        PropTypes.func,
		loadState:        PropTypes.func,
		saveImageDataURI: PropTypes.func,
    isReadOnly:       PropTypes.bool,
    chartType:        PropTypes.string
}
