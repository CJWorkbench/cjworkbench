// This is the main script for the Workflow view

import React from 'react'
import { sortable } from 'react-sortable'
import ModuleMenu from './ModuleMenu'
import { WorkflowNavBar } from './navbar'
import WfModule from './WfModule'
import { getPageID, csrfToken } from './utils'

require('bootstrap/dist/css/bootstrap.css');
require('rc-collapse/assets/index.css');
require('../css/style.css');


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

// ---- WorkflowMain ----


export default class Workflow extends React.Component {
  render() {
    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    var moduleMenu = <ModuleMenu addModule={module_id => this.props.addModule(module_id, this.props.workflow.wf_modules.length)}/>

    // We are a toolbar plus a sortable list of modules
    return (
      <div>
        <WorkflowNavBar addButton={moduleMenu} workflowTitle={this.props.workflow.name}/>
        <SortableList data={this.props.workflow} changeParam={this.props.changeParam} removeModule={this.props.removeModule}/>
      </div>
    );
  }
}




