// This is the main script for the Workflow view

import React from 'react'
import { sortable } from 'react-sortable'
import ModuleLibrary from './ModuleLibrary'
import { WorkflowNavBar } from './navbar'
import WfModule from './WfModule'
import OutputPane from './OutputPane'
import PropTypes from 'prop-types'
import EditableWorkflowName from './EditableWorkflowName'
import WorkflowMetadata from './WorkflowMetadata'
import { getPageID, csrfToken } from './utils'


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
          api={this.props.api}
          outline="list"
          childProps={{
            'data-isReadOnly': this.props.data.read_only,
            'data-wfmodule': item,
            'data-changeParam': this.props.changeParam,
            'data-removeModule': this.props.removeModule,
            'data-revision': this.props.data.revision,
            'data-selected': (item.id == this.props.selected_wf_module),
            'data-api': this.props.api
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
    this.state = {
      isPublic: false,
      privacyModalOpen: false
    };
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.workflow === undefined) {
      return false;
    }

    this.setState({
      isPublic: nextProps.workflow.public
    });
  }

  render() {

    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    var outputPane = null;
    if (this.props.workflow.wf_modules.length > 0) {
      outputPane =  <OutputPane
                      id={this.props.selected_wf_module}
                      revision={this.props.workflow.revision}
                      api={this.props.api}
                    />
    }

    var moduleLibrary = null;
    if (!this.props.workflow.read_only) {
      moduleLibrary = <ModuleLibrary
                        addModule={module_id => this.props.addModule(module_id,
                                      this.props.workflow.wf_modules.length)}
                        api={this.props.api}
                        workflow={this} // We pass the workflow down so that we can toggle the module library visibility in a sensible manner.
                      />
    };



    // Takes care of both, the left-hand side and the right-hand side of the
    // UI. The modules in the workflow are displayed on the left (vertical flow)
    // and the output of the modules on the right.
    // Instead of the output, we see the Module Library UI if the user
    // invokes the Module Library.
    return (
      <div className="workflow-root">

        <WorkflowNavBar
          workflowId={this.props.workflow.id}
          api={this.props.api}
          isReadOnly={this.props.workflow.read_only}
          user={this.props.user}
        />

        <div className="workflow-container">

          {moduleLibrary}

          <div className="modulestack-center">
            <div className="modulestack-header w-75 mx-auto ">
              <br></br>
              <div className="d-flex justify-content-between">
                <div className='editable-title-field mr-2'>
                  <EditableWorkflowName
                    value={this.props.workflow.name}
                    editClass='title-workflow t-d-gray'
                    wfId={this.props.workflow.id}
                    isReadOnly={this.props.workflow.read_only}
                    style={{'width':'100%'}}
                    api={this.props.api}
                  />
                  <WorkflowMetadata workflow={this.props.workflow} api={this.props.api}/>
                </div>
              </div>
            </div>
            <div className="modulestack-list mx-auto ">
              <SortableList
                data={this.props.workflow}
                selected_wf_module={this.props.selected_wf_module}
                changeParam={this.props.changeParam}
                removeModule={this.props.removeModule}
                api={this.props.api}
              />
            </div>
          </div>

          <div className="outputpane-right">
            {outputPane}
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
  removeModule:       PropTypes.func.isRequired,
  user:               PropTypes.object,
  isReadOnly:         PropTypes.boolean
};
