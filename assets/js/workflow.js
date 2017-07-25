// This is the main script for the Workflow view

import React from 'react'
import { sortable } from 'react-sortable'
import ModuleLibrary from './ModuleLibrary'
import { WorkflowNavBar } from './navbar'
import WfModule from './WfModule'
import OutputPane from './OutputPane'
import PropTypes from 'prop-types'
import EditableWorkflowName from './EditableWorkflowName'
import { Button } from 'reactstrap'

import { getPageID, csrfToken } from './utils'

// Are these Require statements redundant?
require('bootstrap/dist/css/bootstrap.css');
require('../css/style.css');


// ---- Sortable WfModules within the workflow ----
var SortableWfModule= sortable(WfModule);

var SortableList = React.createClass({

  getInitialState: function() {
    return {
      draggingIndex: null,
    };
  },

  updateState: function(newState) {
    this.setState(newState);

    // If we've ended a drag, we need to post the new order to the server
    if (newState.draggingIndex === null) {

      // Generate a JSON payload that has only module ID and order, then PATCH
      var newOrder = this.props.data.wf_modules.map( (item, i) => ({id: item.id, order: i}) )

      fetch('/api/workflows/' + getPageID(), {
        method: 'patch',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(newOrder) })
      .catch( (error) => { console.log('Request failed', error); });
    }
  },

  render: function() {
    var listItems = this.props.data.wf_modules.map(function(item, i) {
      return (
        <SortableWfModule
          key={item.id}
          updateState={this.updateState}
          items={this.props.data.wf_modules}
          draggingIndex={this.state.draggingIndex}
          sortId={i}
          outline="list"
          childProps={{
            'data-wfmodule': item,
            'data-changeParam': this.props.changeParam,
            'data-removeModule': this.props.removeModule,
            'data-revision': this.props.data.revision,
            'data-selected': (item.id == this.props.selected_wf_module)
          }}
        />
      );
    }, this);

    return (
          <div className="list">{listItems}</div>
    )
  }
});

// ---- WorkflowMain ----


export default class Workflow extends React.Component {

  constructor(props: iProps) {
    super(props);
    this.state = { moduleLibraryVisible: false };
    this.toggleModuleLibrary = this.toggleModuleLibrary.bind(this)
  }

  // toggles the Module Library between visible or not
  toggleModuleLibrary() {
    this.setState(oldState => ({
      moduleLibraryVisible: !oldState.moduleLibraryVisible
    }));
  }

  render() {
    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    var outputPane = null;
    if (this.props.workflow.wf_modules.length > 0) {
      outputPane = <OutputPane id={this.props.selected_wf_module} revision={this.props.workflow.revision}/>
    }

    var moduleLibrary = <ModuleLibrary 
          addModule={module_id => this.props.addModule(module_id, 
                        this.props.workflow.wf_modules.length)} 
          workflow={this} // We pass the workflow down so that we can toggle the module library visibility in a sensible manner. 
          />

    // Choose whether we want to display the Module Library or the Output Pane.
    var displayPane = null; 
    if (this.state.moduleLibraryVisible) {
        displayPane = moduleLibrary;
    } else {
      displayPane = outputPane;
    }

    // Takes care of both, the left-hand side and the right-hand side of the
    // UI. The modules in the workflow are displayed on the left (vertical flow)
    // and the output of the modules on the right. 
    // Instead of the output, we see the Module Library UI if the user
    // invokes the Module Library. 
    return (
      <div className="workflow-root">
        <WorkflowNavBar workflowId={this.props.workflow.id} api={this.props.api} /><div className="workflow-container">
          <div className="modulestack-left ">
            <div className="modulestack-header w-75 mx-auto ">
              <EditableWorkflowName
                value={this.props.workflow.name}
                editClass='editable-text-field h4 editable-notes-container'
                wfId={this.props.workflow.id} />
              <Button onClick={this.toggleModuleLibrary.bind(this)} 
                  className='button-blue'>Add Module</Button>
            </div>
            <div className="modulestack-list w-75 mx-auto ">
              <SortableList
                data={this.props.workflow}
                selected_wf_module={this.props.selected_wf_module}
                changeParam={this.props.changeParam}
                removeModule={this.props.removeModule}
              />
            </div>
          </div>
          <div className="outputpane-right">
            {displayPane}
          </div>
        </div>
      </div>
    );
  }
}

Workflow.propTypes = {
  api:                PropTypes.object.isRequired,
  workflow:           PropTypes.object,             // not required as fetched after page loads
  selected_wf_module: PropTypes.number,
  addModule:          PropTypes.func.isRequired,
  removeModule:       PropTypes.func.isRequired
};
