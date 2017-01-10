// This is the main script for the Workflow view

import React from 'react'
import ReactDOM from 'react-dom'
import { sortable } from 'react-sortable'
import ModuleMenu from './ModuleMenu.browserify'
import ToolButton from './ToolButton.browserify'
import WfModule from './WfModule.browserify'

// return ID in URL of form "/workflows/id/" or "/workflows/id"
var getPageID = function () {
  var url = window.location.pathname;

  // trim trailing slash if needed
  if (url.lastIndexOf('/' == url.length-1))
    url = url.substring(0, url.length-1);

  // take everything after last slash as the id
  var id = url.substring(url.lastIndexOf('/')+1);
  return id
};

// Add a module to the current workflow
var addModule = function(newModuleID) {

  fetch('/api/workflows/' + getPageID() + "/addmodule", {
    method: 'put',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({insertBefore: 0, moduleID: newModuleID})
  }).then( (response) => { refreshWorkflow() } )
  .catch( (error) => { console.log('Add Module request failed', error); });
};

// Run the current workflow
var executeWorkflow = function() {

  fetch('/api/workflows/' + getPageID() + "/execute", {
    method: 'put',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
  })
  .catch( (error) => { console.log('Execute request failed', error); });
};

// ---- Toolbar and buttons ----


class ToolBar extends React.Component {

  render() {
    return (
      <div>
        <ToolButton text="▶" click={executeWorkflow} />
         <ModuleMenu addModule={addModule}/>
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
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newOrder) })
      .catch( (error) => { console.log('Request failed', error); });
    }
  },

  render: function() {
    var listItems = this.props.data.wf_modules.map(function(item, i) {
      return (
        <SortableWfModule
          key={i}
          updateState={this.updateState}
          items={this.props.data.wf_modules}
          draggingIndex={this.state.draggingIndex}
          sortId={i}
          outline="list"
          childProps={ {'data-module': item.module, 'data-params': item.parameter_vals} } />
      );
    }, this);

    return (
          <div className="list">{listItems}</div>
    )
  }
});

// ---------- Main ----------

// Stores workflow as fetched from server
var currentWorkflow = {}

class WorkflowMain extends React.Component {
  render() {
    return (
      <div>
        <div className="toolbar">
          <ToolBar/>
        </div>
        <SortableList data={currentWorkflow} />
      </div>
    );
  }
}

var renderWorkflow = function ()
{
  ReactDOM.render(
      <WorkflowMain/>,
      document.getElementById('root')
  );
}

// Reload workflow from server, set props
var refreshWorkflow = function() {
  fetch('/api/workflows/' + getPageID())
  .then(response => response.json())
  .then(json => {
    currentWorkflow = json;
    renderWorkflow();
  })
}

// Load the page!
refreshWorkflow();
