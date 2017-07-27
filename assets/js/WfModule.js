// UI for a single module within a workflow

import React from 'react'
import WfParameter from './WfParameter'
import TableView from './TableView'
import WfModuleContextMenu from './WfModuleContextMenu'
import EditableNotes from './EditableNotes'
import { store, wfModuleStatusAction } from './workflow-reducer'
import { csrfToken } from './utils'
import * as Actions from './workflow-reducer'
import PropTypes from 'prop-types'

// Libraries to provide a collapsable table view
import { Collapse, Button, CardBlock, Card } from 'reactstrap';

// ---- StatusBar ----

class StatusBar extends React.Component {
  render() {

    var barColor = undefined;

    switch (this.props.status) {
      case 'ready':
        barColor = 'module-output-bar-blue';
        break;
      case 'busy':
        barColor = 'module-output-bar-orange';
        break;
      case 'error':
        barColor = 'module-output-bar-red';        
        break;
      default:
        barColor = 'module-output-bar-white';        
        break;
    }
    return <div className={barColor}></div>
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

// ---- WfModule ----

export default class WfModule extends React.Component {

  constructor(props) {
    super(props);
    this.initFields(props);
    this.state = {
      detailsOpen: false,
      showNotes: false
    };           // componentDidMount will trigger first load    
    this.click = this.click.bind(this);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
    this.removeModule = this.removeModule.bind(this);
    this.toggleDetails = this.toggleDetails.bind(this);
    this.showNotes = this.showNotes.bind(this);
    this.hideNotes = this.hideNotes.bind(this);
  }

  // our props are annoying (we use data- because Sortable puts all these props om the DOM object)
  // so save them into this
  initFields(props) {
    this.wf_module = props['data-wfmodule'];
    this.module = this.wf_module.module_version.module;
    this.params = this.wf_module.parameter_vals;
    this.revision = props['data-revision'];
  }

  // alas, the drawback of the convienence of initFields is we need to call it whenever props change
  componentWillReceiveProps(newProps) {
    this.initFields(newProps)
  }

  // We become the selected module on any click
  click(e) {
    Actions.store.dispatch(Actions.changeSelectedWfModuleAction(this.wf_module.id));
  }

  // These functions allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  // Suppresses reassignment of the same text, which can be important to avoid endless notification loops
  setParamText(id_name, text) {
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p && text != p.string) {
      this.props['data-changeParam'](p.id, { value: text })
    }
  }

  getParamText(id_name) {
    //console.log("getParamText " + id_name)
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p) {
      return p.value;
    }
  }

  removeModule(e) {
    this.props['data-removeModule'](this.wf_module.id);
  }

  toggleDetails() {
    this.setState(Object.assign({}, this.state, {detailsOpen: !this.state.detailsOpen}));
  }

  showNotes(e) {
    e.stopPropagation();
    this.setState(Object.assign({}, this.state, {showNotes: true}));
  }

  hideNotes() {
    this.setState(Object.assign({}, this.state, {showNotes: false}));
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
          lastUpdateCheck={this.wf_module.last_update_check}
          getParamText={this.getParamText}
          setParamText={this.setParamText} 
        />
      });

    var inside = undefined;
    if (this.state.detailsOpen)
      inside = <div className='wf-parameters'>{paramdivs}</div>;

    var notes = undefined;
    var value = ( this.wf_module.notes && (this.wf_module.notes != "") ) 
      ? this.wf_module.notes
      : "Write notes here"
    if (this.state.showNotes)
      notes = <EditableNotes
                value={value}
                hideNotes={ () => this.hideNotes() }
                editClass='editable-notes-field'
                wfModuleId={this.wf_module.id} />

    var notesIcon = undefined;
    if (!this.state.showNotes)
      notesIcon = <div className='context-button p-0 mt-0.5 d-flex align-items-center' onClick={this.showNotes}>
                    <div className='icon-note button-icon' ></div>
                  </div>

    var arrow = (this.state.detailsOpen) 
      ? <div className='icon-sort-up button-icon'></div>
      : <div className='icon-sort-down button-icon'></div>
      

    // Putting it all together: name, status, parameters, output
    return (
      <div className='container' {...this.props} onClick={this.click}>
        <div className='card mb-2'>
          {/* --- The whole card --- */}          
          <div className='card-block p-0 module-card-wrapper d-flex justify-content-between'>            
            {/* --- Everything but the status bar, on the left of card --- */}
            <div className='module-card-info p-2'>
              {notes} 
              <div 
                className='module-card-header mb-2 pt-2 '
                onClick={this.toggleDetails}
              >
                {/* TODO: attach icon names to modules, call via 'this.module.icon' */}
                <div className='d-flex justify-content-start'>
                  <div className='icon-url module-icon m-1'></div>
                  <h4 className='text-center mb-0 ml-2 mt-2 module-library-line-item-title'>
                    {this.module.name}
                  </h4>
                  <div className='context-button ml-1 mt-1'>
                    {arrow}
                  </div>
                </div>
                {/* TODO: not necessary to pass in stopProp*/}
                <div className='d-flex justify-content-end'>
                  {notesIcon}
                  <WfModuleContextMenu 
                    removeModule={ () => this.removeModule() }
                    stopProp={(e) => e.stopPropagation()}
                    id={this.wf_module.id}
                    className='menu-test-class'
                  />
                </div>
              </div>
              {/* --- Error messages appear here --- */}
              <StatusLine status={this.wf_module.status} error_msg={this.wf_module.error_msg} />
              {/* --- Module details, will expand / collapse --- */}              
              <Collapse className='mt-1 pl-2 pr-2' isOpen={this.state.detailsOpen} >
                {inside}
              </Collapse>
            </div>
            {/* --- Color indicator of module status, on the right of card --- */}
            <div className='output-bar-container'>  
              <StatusBar status={this.wf_module.status}/>
            </div>
          </div>
        </div>
      </div>
    ); 
  } 
}


WfModule.propTypes = {
  'data-wfmodule':      PropTypes.object,
  'data-revison':       PropTypes.number,
  'data-selected':      PropTypes.bool,
  'data-changeParam':   PropTypes.func,
  'data-removeModule':  PropTypes.func
};
