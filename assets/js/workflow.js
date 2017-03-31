// This is the main script for the Workflow view

import React from 'react'
import ReactDOM from 'react-dom'
import { Provider, connect } from 'react-redux'
import { sortable } from 'react-sortable'
import ModuleMenu from './ModuleMenu'
import ToolButton from './ToolButton'
import WfModule from './WfModule'
import * as Actions from './workflow-reducer'
import { getPageID, csrfToken } from './utils'

require('../css/style.css');


// ---- Toolbar and buttons ----


class ToolBar extends React.Component {

  render() {
    return (
      <div>
         <ModuleMenu addModule={this.props.onAddModuleClick}/>
      </div>
    ); 
  } 
}

// ---- Sortable Modules ----

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

      // Generate a JSON paylod that has only module ID and order, then PATCH
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
          childProps={ {'data-wfmodule': item, 'data-changeParam': this.props.changeParam, 'data-removeModule': this.props.removeModule, 'data-revision': this.props.data.revision } } />
      );
    }, this);

    return (
          <div className="list">{listItems}</div>
    )
  }
});

// ---------- Main ----------


class WorkflowMain extends React.Component {
  render() {
    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    // We are a toolbar plus a sortable list of modules
    return (
      <div>
        <div className="toolbar">
          <ToolBar onAddModuleClick={module_id => this.props.addModule(module_id, this.props.workflow.wf_modules.length)}/>
        </div>
        <SortableList data={this.props.workflow} changeParam={this.props.changeParam} removeModule={this.props.removeModule}/>
      </div>
    );
  }
}


// ---- Workflow container ----

function onParamChanged(paramID, newVal) {
  console.log('Changing parameter ' + paramID);
   fetch('/api/parameters/' + paramID, {
      method: 'patch',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(newVal)
    })
}

// Handles addModule (and any other actions that change top level workflow state)
const mapStateToProps = (state) => {
  return {
    workflow: state.workflow,
  }
}

const mapDispatchToProps = (dispatch) => {
  return {
    addModule: (module_id, insertBefore) => {
      dispatch(Actions.addModuleAction(module_id, insertBefore))
    },
    removeModule: (wf_module_id) => {
      dispatch(Actions.removeModuleAction(wf_module_id))
    },
    changeParam: (paramID, newVal) => {
      onParamChanged(paramID, newVal)
    }
  }
}


const WorkflowContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(WorkflowMain)


// ---- Main ----

// Render with Provider to root so all objects in the React DOM can access state
ReactDOM.render(
    <Provider store={Actions.store}>
      <WorkflowContainer/>
    </Provider>,
    document.getElementById('root')
);

// Load the page!
Actions.store.dispatch(Actions.reloadWorkflowAction())

// Start listening for events
const socket = new WebSocket("ws://" + window.location.host + "/workflows/" + getPageID());

socket.onmessage = function(e) {
  var data = JSON.parse(e.data);
  console.log("Got ws message: " + e.data);
  if ('type' in data) {
    switch (data.type) {

      case 'wfmodule-status':
        Actions.store.dispatch(Actions.wfModuleStatusAction(data.id, data.status, data.error_msg ? data.error_msg : ''));
        return

      case 'reload-workflow':
        Actions.store.dispatch(Actions.reloadWorkflowAction());
        return
    }
  }
}
