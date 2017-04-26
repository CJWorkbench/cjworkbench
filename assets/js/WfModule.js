// UI for a single module within a workflow

import React, { PropTypes } from 'react'
import ChartParameter from './Chart'
import { store, wfModuleStatusAction } from './workflow-reducer'
import { csrfToken } from './utils'

// Libraries to provide a collapsable table view
import { Collapse, Button, CardBlock, Card } from 'reactstrap';
import ReactDataGrid from 'react-data-grid';


// ---- WfParameter - a single editable parameter ----

class WfParameter extends React.Component {

  constructor(props) {
    super(props);

    this.type = this.props.p.parameter_spec.type;
    this.name = this.props.p.parameter_spec.name;

    this.keyPress = this.keyPress.bind(this);
    this.blur = this.blur.bind(this);
    this.click = this.click.bind(this);
  }

  paramChanged(e) {
    // console.log("PARAM CHANGED");
    var newVal = {};
    newVal[this.type] = e.target.value;
    this.props.changeParam(this.props.p.id, newVal);
  }

  // Save value (and re-render) when user presses enter or we lose focus
  // Applies only to non-text fields
  keyPress(e) {
    if (this.type != 'text' && e.key == 'Enter') {
        this.paramChanged(e);
        e.preventDefault();       // eat the Enter so it doesn't get in out input field
    }
  }

  blur(e) {
    this.paramChanged(e);
  }

  // Send event to server for button click
  click(e) {
    if (this.type == 'button') {
      var url = '/api/parameters/' + this.props.p.id + '/event';
      var eventData = {'type': 'click'};
      fetch(url, {
        method: 'post',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(eventData)
      }).then(response => {
        if (!response.ok)
          store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', response.statusText))
      });
    }
    if (this.type == 'checkbox') {
        var newVal = {};
        newVal[this.type] = e.target.checked;
        this.props.changeParam(this.props.p.id, newVal);
    }
  }

  render() {
    if (!this.props.p.visible) {
      return false; // nothing to see here
    }

    switch (this.type) {
      case 'string':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleStringInput' rows='1' defaultValue={this.props.p.string} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'number':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleNumberInput' rows='1' defaultValue={this.props.p.number} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'text':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleTextInput' rows='4' defaultValue={this.props.p.text} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'button':
        return (
          <div>
            <button className='btn btn-secondary' onClick={this.click}>{this.name}</button>
          </div>
        );

      case 'checkbox':
        return (
            <div>
                <label className='mr-1'>{this.name}:</label>
                <input type="checkbox" checked={this.props.p.checkbox} onChange={this.click}></input>
            </div>
        );

      case 'custom':

        // Load and save chart state, image to hidden parameters
        var loadState = ( () => this.props.getParamText('chartstate') );
        var saveState = ( state => this.props.setParamText('chartstate', state) );

        var saveImageDataURI = ( state => this.props.setParamText('chart', state) );

        return (
          <div>
            <a href={'/public/paramdata/live/' + this.props.p.id + '.png'}>PNG</a>
            <ChartParameter
              wf_module_id={this.props.wf_module_id}
              revision={this.props.revision}
              saveState={saveState}
              loadState={loadState}
              saveImageDataURI={saveImageDataURI}
            />
          </div>
        );

      default:
        return null;  // unrecognized parameter type
    }
  }
}

WfParameter.propTypes = {
  p:                React.PropTypes.object,
  wf_module_id:     React.PropTypes.number,
	revision:         React.PropTypes.number,
  changeParam:      React.PropTypes.func,
	getParamText:     React.PropTypes.func,
	setParamText:     React.PropTypes.func,
};


// ---- StatusLight ----
// Ready, Busy, or Error
class StatusLight extends React.Component {
  render() {
    return <div className={this.props.status + '-light'}></div>
  }
}

// ---- StatusLine ----
// Display error message, if any
class StatusLine extends React.Component {
  render() {
    if (this.props.status == 'error') {
      return <div className='wfModuleErrorMsg'>{this.props.error_msg}</div>
    } else if (this.props.status == 'busy') {
      return <div className='wfModuleErrorMsg'>Working...</div>
    } else {
      return false
    }
  }
}

// ---- CollapseSection ---
// Higher-order component that does a classic twirly collapse, inside a rounded border

function CollapseSection(WrappedComponent, title, startOpen ) {
  return class extends React.Component {
    constructor(props) {
      super(props);
      this.state = {isOpen: startOpen};           // componentDidMount will trigger first load
      this.toggle = this.toggle.bind(this);
    }

    toggle() {
      this.setState({isOpen: !this.state.isOpen});
    }

    render() {
      return(
        <div className='panel-wrapper m-0 p-1'>
          <div onClick={this.toggle}> { (this.state.isOpen ? '\u25be' : '\u25b8') + ' ' + title}</div>
          <Collapse className='mt-1 pl-2 pr-2' isOpen={this.state.isOpen}>
            <WrappedComponent {...this.props}/>
          </Collapse>
        </div>
      );
    }
  }
}

// ---- TableView ----
// Displays the module's rendered output, if any


class TableView extends React.Component {
  constructor(props) {
    super(props);
    this.state = { tableData: [], loading: false, isOpen: false };           // componentDidMount will trigger first load
    this.loadingState = { tableData: [], loading: true };
    this.toggle= this.toggle.bind(this);
  }

  // Load table data from render API
  loadTable() {
    var self = this;
    var url = '/api/wfmodules/' + this.props.id + '/render';
    fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        self.setState(Object.assign({}, this.state, {tableData: json, loading: false}));
      }); // triggers re-render
  }

  // Load table when first rendered
  componentDidMount() {
    this.loadTable()
  }

  // If the revision changes from under us reload the table, which will trigger a setState and re-render
  componentWillReceiveProps(nextProps) {
    //console.log("willRecieveProps " + this.props.id);
    //console.log('old revision ' + this.props.revision + ' new revision ' + nextProps.revision);

    if (this.props.revision != nextProps.revision) {
      this.setState(Object.assign({}, this.state, this.loadingState));               // "unload" the table
      this.loadTable();
    }
  }

  // Update only when we are not loading
  shouldComponentUpdate(nextProps, nextState) {
    return !nextState.loading;
  }

  toggle() {
    this.setState(Object.assign({}, this.state, { isOpen: !this.state.isOpen}));
  }

  render() {
    var tableData = this.state.tableData;
    var table;

    // Generate the table if there's any data
    if (tableData.length > 0 && !this.state.loading) {
      var columns = Object.keys(tableData[0]).filter(key => key!='index').map( key => { return { 'key': key, 'name': key, 'resizable':true } });
      table = <ReactDataGrid
        columns={columns}
        rowGetter={ i => tableData[i] }
        rowsCount={tableData.length}
        minHeight={500} />;
    }  else {
      table = <p>(no data)</p>;
    }

    return table;
  }
}



// ---- WfModule ----

//  Some convenient components that collapse params, output
const CollapsibleTableView = CollapseSection(
  TableView,
  'Output',
  true);     // don't start open

const ParamDivsComponent = (props) => <div>{props.paramDivs}</div>
const CollapsibleParams = CollapseSection(
  ParamDivsComponent,
  'Settings',
  true);         // start open

export default class WfModule extends React.Component {

  constructor(props) {
    super(props);
    this.initFields(props);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
    this.removeModule = this.removeModule.bind(this);
  }

  componentWillReceiveProps(newProps) {
    this.initFields(newProps)
  }

  // our props are annoying (we use data- because Sortable puts all these props om the DOM object)
  // so save them into this
  initFields(props) {
    this.wf_module = props['data-wfmodule'];
    this.module = this.wf_module.module;
    this.params = this.wf_module.parameter_vals;
    this.revision = props['data-revision'];
  }

  // These functions allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  // Suppresses reassignment of the same text, which can be important to avoid endless notification loops
  setParamText(id_name, text) {
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p && text != p.text) {
      this.props['data-changeParam'](p.id, { text: text })
    }
  }

  getParamText(id_name) {
    //console.log("getParamText " + id_name)
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p) {
      return p.text;
    }
  }

  removeModule() {
    this.props['data-removeModule'](this.wf_module.id);
  }

  render() {

    // Each parameter gets a WfParameter
    var paramdivs = this.params.map((ps, i) => {
        return <WfParameter
          key={i}
          p={ps}
          changeParam={this.props['data-changeParam']}
          wf_module_id={this.wf_module.id}
          revision={this.revision}
          getParamText={this.getParamText}
          setParamText={this.setParamText} />
      });

    // Putting it all together: name, status, parameters, output
    return (
      <div className='container' {...this.props} >
        <div className='card w-75 mx-auto mb-4 bg-faded'>
          <div className='card-block drop-shadow p-1'>

            <div className='d-flex justify-content-between align-items-center mb-2'>
                <button type='button' className='btn btn-secondary btn-sm' onClick={this.removeModule}>&times;</button>
                <h3 className='text-center mb-0'>{this.module.name}</h3>
                <StatusLight status={this.wf_module.status}/>
            </div>
            <StatusLine status={this.wf_module.status} error_msg={this.wf_module.error_msg} />
            <CollapsibleParams paramDivs={paramdivs}/>
            <CollapsibleTableView id={this.wf_module.id} statusReady={this.wf_module.status == 'ready'} revision={this.revision} />
            <a className='ml-2' href={'/public/moduledata/live/' + this.wf_module.id + '.csv'}>CSV</a>/<a href={'/public/moduledata/live/' + this.wf_module.id + '.json'}>JSON</a>
          </div>

        </div>
      </div>
    ); 
  } 
}

