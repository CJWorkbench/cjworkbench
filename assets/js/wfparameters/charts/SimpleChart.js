// Chart JSX component wraps a ChartBuilder

import React from 'react'
import { store, wfModuleStatusAction } from '../../workflow-reducer'
import PropTypes from 'prop-types'

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
    this.onStateChange = this.onStateChange.bind(this);
    this.saveImage = this.saveImage.bind(this);

    // I kinda hate this... we store the last chart state we were given here, to suppress unnecessary API calls.
    // We can't put it in React state because we don't want to trigger a render... and this state doesn't change
    // the render, as this value is passed to us by the ChartBuilder component, so it's already rendered.
    // Only tricky bit is to remember to reset this when our props change.
    this.lastChartStateString = null;
  }

  componentWillMount(props) {
    var modelText = this.props.loadState();
    var model;
    var defaults = chartConfig.xy.defaultProps;

    if (modelText !== "") {
      model = JSON.parse(this.props.loadState());
    } else {
      model = defaults;
    }

    model.chartProps.input = {raw: ''} //blank data to start

    this.loadingState = { loading: true, loaded_ever: true };

    this.setState({ loading: true, loaded_ever: false });

    defaults.chartProps.chartSettings[0].type = this.props.chartType || 'line';
    defaults.chartProps.scale.typeSettings.maxLength = 7;

    ChartPropertiesStore.addChangeListener(this.onStateChange);
    ChartMetadataStore.addChangeListener(this.onStateChange);
    ErrorStore.addChangeListener(this.onStateChange);
    SessionStore.addChangeListener(this.onStateChange);

    ChartServerActions.receiveModel(model);
  }

  getStateFromStores() {
  	return {
  		chartProps: ChartPropertiesStore.getAll(),
  		metadata: ChartMetadataStore.getAll(),
  		errors: ErrorStore.getAll(),
  		session: SessionStore.getAll()
  	};
  }

  // Turn ChartBuilder errors into module errors (so user gets the red light etc.)
  parseErrors(errors) {
    var errorMessage = errors.messages.map( (m) => {
      return m.text + "\r\n";
    });
    if (errorMessage !== '') {
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', errorMessage))
    } else {
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'ready'))
    }
  }

  // Store ChartBuilder state and PNG image into our hidden parameters
  saveState(model) {
    // Store chart parameters. Don't store chart data, that comes from input
    var model2 = Object.assign({}, model, {errors: undefined}); // don't alter real model!
    model2.chartProps = Object.assign({}, model2.chartProps, {data: undefined, input:undefined});
    var stateString = JSON.stringify(model2);

    // Save to server only if there is something to save
    if (stateString != this.lastChartStateString) {
      // console.log("saving chart state");
      this.props.saveState(stateString);
      this.lastChartStateString = stateString;
    }
  }

  // Store most recently rendered chart image
  saveImage() {
    // console.log("saveImage");
    var el = document.getElementsByClassName('renderer-svg-desktop')[0];
    // console.log(el);
    if (el) {
      var chartNode = el.getElementsByClassName('chartbuilder-svg')[0]
      // console.log(chartNode);

      if (chartNode) {
        saveSvgAsPng.svgAsPngUri(chartNode, {}, dataURI => {
          this.props.saveImageDataURI(dataURI)
        })
      }
    }
  }

  // called when any change is made to chart. Update error status, save to hidden 'chartstate' text field
  onStateChange(_uh) {
    var model = this.getStateFromStores();
    this.parseErrors(model.errors);
    this.saveState(model);
    this.setState(Object.assign({}, {loading: false, loaded_ever: true}, model));
  }

  // Load our input data from render API, restore start state from hidden param
  loadChart() {
    this.setState(this.loadingState);
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        var input = { raw: JSONtoCSV(json.rows) };
        ChartViewActions.updateInput('input', input);
      });
  }

  // Load input data, settings when first rendered
  componentDidMount() {
    this.loadChart();
  }

  // If the revision changes from under us reload the table, which will trigger a setState and re-render
  componentWillReceiveProps(nextProps) {
    if (this.props.revision != nextProps.revision) {
      this.loadChart();
    }
    this.lastChartStateString= null;  //  in theory, we could be a different parameter now!
  }

  // Update only when we are not loading
  shouldComponentUpdate(nextProps, nextState) {
    return !nextState.loading;
  }

  render() {
    if (this.state.loaded_ever && this.state.errors.valid) {
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
      return false;
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
