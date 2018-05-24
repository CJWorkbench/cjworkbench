// Chart JSX component wraps a ChartBuilder

import React from 'react'
import PropTypes from 'prop-types'
import { errorText } from './errors'
import ExportChart from './ExportChart'

var ChartViewActions = require("chartbuilder/src/js/actions/ChartViewActions");
var chartConfig = require("chartbuilder/src/js/charts/chart-type-configs");

//var saveSvgAsPng = require("save-svg-as-png");

/* Flux stores */
var RendererWrapper = require("chartbuilder/src/js/components/RendererWrapper");
var ChartServerActions = require("chartbuilder/src/js/actions/ChartServerActions");
var ChartPropertiesStore = require("chartbuilder/src/js/stores/ChartPropertiesStore");
var ChartMetadataStore = require("chartbuilder/src/js/stores/ChartMetadataStore");
var SessionStore = require("chartbuilder/src/js/stores/SessionStore");
var ErrorStore = require("chartbuilder/src/js/stores/ErrorStore");

// Do we actually need to do require for these?
var ChartExport = require("chartbuilder/src/js/components/ChartExport");

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
      text += colnames.map((name) => {return "\"" + row[name] + "\""}).join(',') + '\n';
    }
    return text;
  } else {
    return '';
  }
}

export default class SimpleChartParameter extends React.Component {

  constructor(props) {
    super(props);
    this.state = { loading: true };
    this.onStateChange = this.onStateChange.bind(this);
    this.onErrorChange = this.onErrorChange.bind(this);
    this.loadChartProps = this.loadChartProps.bind(this);
    this.windowWillReceiveData = this.windowWillReceiveData.bind(this);
    // Refs can't be passed directly in the render function from parent to child, so instead we set a variable and
    // define a getter function that the child component can call.
    this.parentRef = null;
    this.getParentRef = this.getParentRef.bind(this);
  }

  // called when any change is made to chart. Update error status.
  onStateChange(errors) {
    let model = this.getStateFromStores();
    let errorState;
    if (errors) {
        errorState = {errors: errors, loading: !errors.valid}
    }
    this.setState(Object.assign({}, model, errorState));
  }

  // called when errors return -- they need to be handled seperately
  onErrorChange() {
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
  loadChart(data) {
    return { raw: JSONtoCSV(data.rows) };
  }

  displaySettings(){
    return {
    	labelRectSize: "0.6em",
    	labelXMargin: "0.6em",
    	labelTextMargin: "0.3em",
    	labelRowHeight: "1.2em",
    	afterTitle: "1.4em",
    	afterLegend: "1em",
    	blockerRectOffset: "0.2em",
    	lineMarkThreshold: 10, // render marks (dots) on lines if data < N
    	columnOuterPadding: 0.01, // % of width to pad for columns
    	columnInnerPadding: 0, // % of col group width to pad btwn each
    	minPaddingOuter: "1em",
    	bottomPaddingWithoutFooter: "3em",
    	yAxisOrient: {
    		primaryScale: "left",
    		secondaryScale: "right",
    	},
    	aspectRatio: {
    		wide: (9 / 16),
    		longSpot: (4 / 3),
    		smallSpot: (3 / 4)
    	},
    	margin: {
    		top: "2rem",
    		right: "5rem",
    		bottom: "5rem",
    		left: "5rem"
    	},
    	padding: {
    		top: 0,
    		right: 0,
    		bottom: 0,
    		left: 0
    	}
    };
  }

  loadChartProps(modelText, data) {
    let model;
    let defaults = chartConfig.xy.defaultProps;
    chartConfig.xy.display=this.displaySettings();

    defaults.chartProps.chartSettings[0].type = this.props.chartType || 'line';
    defaults.chartProps.scale.typeSettings.maxLength = 15;
    defaults.chartProps.scale.typeSettings.tickFont = '10px Khula-Light';

    if (modelText !== "") {
      model = JSON.parse(modelText);
      this.lastChartStateString = modelText;
    } else {
      model = defaults;
    }
    model.chartProps.input = data
    return model;
  }

  // Load input data, settings when first rendered
  componentDidMount() {
    ChartPropertiesStore.addChangeListener(this.onStateChange);
    ChartMetadataStore.addChangeListener(this.onStateChange);
    SessionStore.addChangeListener(this.onStateChange);
    ErrorStore.addChangeListener(this.onErrorChange);

    let data = this.loadChart(workbench.input);

    let modelText = workbench.params.chart_editor;
    let newModel = this.loadChartProps(modelText, data);
    ChartServerActions.receiveModel(newModel);
    ChartViewActions.updateInput('input', data);
    this.setState({loading: false});

    window.addEventListener('message', this.windowWillReceiveData, false);
  }

  componentWillUnmount() {
		ChartPropertiesStore.removeChangeListener(this.onStateChange);
		ChartMetadataStore.removeChangeListener(this.onStateChange);
		SessionStore.removeChangeListener(this.onStateChange);
		ErrorStore.removeChangeListener(this.onErrorChange);
	}

  windowWillReceiveData(event) {
    ChartServerActions.receiveModel(event.data.model);
  }

  getParentRef() {
    return this.parentRef;
  }

  render() {
    if (!this.state.loading && typeof this.state.errors !== 'undefined')  {
      return (
        <div ref={(ref) => {this.parentRef = ref}}>
          <ExportChart targetSvgWrapperClassname="rendered-svg" />
          <RendererWrapper
            editable={false}
            showMetadata={true}
            model={this.state}
            enableResponsive={true}
            className="rendered-svg"
            svgClassName="rendered-svg-class-name"
            parentRef={this.getParentRef} />
        </div>
      )
    } else {
      return <div></div>;
    }
  }
}

SimpleChartParameter.propTypes = {
    chartType:        PropTypes.string
};
