// Chart JSX component wraps a ChartBuilder

import React from 'react'
import { store, wfModuleStatusAction } from '../workflow-reducer'
import PropTypes from 'prop-types'


var Chartbuilder = require("chartbuilder/src/js/components/Chartbuilder");
var ChartServerActions = require("chartbuilder/src/js/actions/ChartServerActions");
var chartConfig = require("chartbuilder/src/js/charts/chart-type-configs");
var saveSvgAsPng = require("save-svg-as-png");

require("../../css/chartbuilder_fonts_colors.css");
require("chartbuilder-ui/dist/styles.css");

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
    this.loadingState = { loading: true, loaded_ever: true };
    this.state = { loading: false, loaded_ever: false }; // componentDidMount will trigger first load
    this.onStateChange = this.onStateChange.bind(this);
    this.saveImage = this.saveImage.bind(this);

    // I kinda hate this... we store the last chart state we were given here, to suppress unnecessary API calls.
    // We can't put it in React state because we don't want to trigger a render... and this state doesn't change
    // the render, as this value is passed to us by the ChartBuilder component, so it's already rendered.
    // Only tricky bit is to remember to reset this when our props change.
    this.lastChartStateString = null;
  }

  // Turn ChartBuilder errors into module errors (so user gets the red light etc.)
  parseErrors(errors) {
    var first_err= errors.messages.find(m => m.type=='error');
    if (first_err) {
//      console.log("Chart errors");
      store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', first_err.text))
    } else {
//      console.log("Chart no errors");
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
  onStateChange(model) {
    // console.log('onStateChange');
    this.parseErrors(model.errors);
    this.saveState(model)
  }

  // Load our input data from render API, restore start state from hidden param
  loadChart() {
    this.setState(this.loadingState);
    var self = this;
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {

        var model;
        var modelText = this.props.loadState();
        if (modelText == '') {
          // never had a chart before, start with defaults
          model = Object.assign( {}, chartConfig.xy.defaultProps );
          //console.log("loading defaults");
        } else {
          model = JSON.parse(this.props.loadState()); // retrieve from hidden param
          model.chartProps.data = [];
          //console.log("loading from param");
        }

        // Add this module's input data to the chart properties we just loaded
        model.chartProps.input = { raw: JSONtoCSV(json.rows) };

        //console.log("Updating chart");
        //console.log(model);
        ChartServerActions.receiveModel(model);

        this.setState({loading: false, loaded_ever: true});

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
    // Don't render until we've set chart data at least once
    if (this.state.loaded_ever) {
      return (<Chartbuilder
        autosave={!this.props.isReadOnly}
        editable={!this.props.isReadOnly}
        onStateChange={this.onStateChange}
        postRender={this.saveImage}
        showDataInput={false}
        showExport={false}
        showLoadPrevious={false}/>);
    } else {
      return false;
    }
  }
}

ChartParameter.propTypes = {
		wf_module_id:     PropTypes.number,
		revision:         PropTypes.number,
		saveState:        PropTypes.func,
		loadState:        PropTypes.func,
		saveImageDataURI: PropTypes.func,
    isReadOnly:       PropTypes.bool
}
