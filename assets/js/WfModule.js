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
import workbenchapi from './WorkbenchAPI';

// Libraries to provide a collapsable table view
import { Collapse, Button, CardBlock, Card } from 'reactstrap';

// ---- StatusBar ----

class StatusBar extends React.Component {
  render() {

    var barColor = undefined;

    switch (this.props.status) {
      case 'ready':
        barColor = (this.props.isSelected) ? 'module-output-bar-blue' : 'module-output-bar-white'
        break;
      case 'busy':
        barColor = 'module-output-bar-orange';
        break;
      case 'error':
        barColor = (this.props.isSelected) ? 'module-output-bar-red' : 'module-output-bar-pink'
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
// BUG - Tying this to Props will ensure that error message stays displayed, even after resolution
class StatusLine extends React.Component {
  render() {
    if (this.props.status == 'error') {
      return <div className='wf-module-error-msg mb-3'>{this.props.error_msg}</div>
    } else if (this.props.status == 'busy') {
      return <div className='wf-module-error-msg mb-3'>Working...</div>
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
      isCollapsed: this.wf_module.is_collapsed,
      showNotes: false
    };           // componentDidMount will trigger first load
    this.click = this.click.bind(this);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
    this.removeModule = this.removeModule.bind(this);
    this.showNotes = this.showNotes.bind(this);
    this.hideNotes = this.hideNotes.bind(this);
    this.toggleCollapsed = this.toggleCollapsed.bind(this);

    this.api = workbenchapi();
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
    this.setState({isCollapsed: this.wf_module.is_collapsed});
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
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p) {
      return p.value;
    }
  }

  removeModule(e) {
    this.props['data-removeModule'](this.wf_module.id);
  }

  // Sets state on the server, which should result in a callback that will
  // update the state. This state update will then drive the display render.
  toggleCollapsed() {
    this.api.toggleWfModuleCollapsed(this.wf_module.id, !this.state.isCollapsed);
  }

  showNotes(e) {
    e.stopPropagation();
    this.setState(Object.assign({}, this.state, {showNotes: true}));
  }

  hideNotes() {
    this.setState(Object.assign({}, this.state, {showNotes: false}));
  }

  render() {

    var updateSettings = {
      lastUpdateCheck:  this.wf_module.last_update_check,
      autoUpdateData:   this.wf_module.auto_update_data,
      updateInterval:   this.wf_module.update_interval,
      updateUnits:      this.wf_module.update_units
    }

    // Each parameter gets a WfParameter
    console.log(this.props);
    var paramdivs = this.params.map((ps, i) => {
        return <WfParameter
          isReadOnly={this.props.isReadOnly}
          key={i}
          p={ps}
          changeParam={this.props['data-changeParam']}
          wf_module_id={this.wf_module.id}
          revision={this.revision}
          updateSettings={updateSettings}
          getParamText={this.getParamText}
          setParamText={this.setParamText}
        />
      });

    var inside = undefined;

    if (!this.state.isCollapsed)
      inside = <div className='module-card-params'>{paramdivs}</div>;

    var notes = undefined;
    var value = ( this.wf_module.notes && (this.wf_module.notes != "") )
      ? this.wf_module.notes
      : "Write notes here"
    if (this.state.showNotes)
      notes = <EditableNotes
                isReadOnly={this.props.isReadOnly}
                value={value}
                hideNotes={ () => this.hideNotes() }
                editClass='editable-notes-field t-d-gray note'
                wfModuleId={this.wf_module.id} />

    var notesIcon = undefined;
    if (!this.state.showNotes)
      notesIcon = <div className='context-button' onClick={this.showNotes}>
                    <div className='icon-note button-icon' ></div>
                  </div>

    var arrow = (this.state.isCollapsed)
      ? <div className='icon-sort-down button-icon ml-3'></div>
      : <div className='icon-sort-up button-icon ml-3'></div>

    // Putting it all together: name, status, parameters, output
    return (
      <div className='container' {...this.props} onClick={this.click}>
        <div className='card'>
          {/* --- The whole card --- */}
          <div className='card-block module-card-wrapper d-flex justify-content-between'>
            {/* --- Everything but the status bar, on the left of card --- */}
            <div className='module-card-info'>
              {notes}
              <div
                className='module-card-header'
                onClick={this.toggleCollapsed}
              >
                {/* TODO: attach icon names to modules, call via 'this.module.icon' */}
                <div className='d-flex justify-content-start'>
                  <div className='icon-url module-icon'></div>
                  <div className='t-d-gray title-4'>
                    {this.module.name}
                  </div>
                  <div className=''>
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

              <Collapse className='' isOpen={!this.state.isCollapsed} >
                {inside}
              </Collapse>
            </div>
            {/* --- Color indicator of module status, on the right of card --- */}
            <div className='output-bar-container'>
              <StatusBar 
                status={this.wf_module.status}
                isSelected={this.props['data-selected']}
              />
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
