// Drop-down menu on Workflows page, 
// triggered by click on three-dot icon next to listed workflow

import React from 'react';
import { csrfToken, goToUrl } from './utils';
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap';

export default class WorkflowContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      workflows: []
    };
  }
  
  deleteOption(id) {
    console.log("Clicked the Delete selection in WorkflowContext Menu for ID: " + id);
    this.deleteWorkflow(id);
  }

  // Ask the user if they really wanna do this. If sure, post DELETE to server
  // TO FIX: Does not automatically reload page with new WF list after deletion 
  deleteWorkflow(id) {
    if (!confirm("Permanently delete this workflow?"))
      return;
    var _this = this;

    fetch(
      '/api/workflows/' + id ,
      {
        method: 'delete',
        credentials: 'include',
        headers: {
          'X-CSRFToken': csrfToken
        }
      }
    )
    .then(response => {
      if (response.ok) {
        var workflowsMinusID = this.state.workflows.filter(wf => wf.id != id);
        _this.setState({workflows: workflowsMinusID, newWorkflowName: this.state.newWorkflowName})
      }
    })
  }

  // \u22EE = three-dot menu icon in Unicode 
  render() {
    return (
       <UncontrolledDropdown>
        <DropdownToggle>
          {'\u22EE'}
        </DropdownToggle>
        <DropdownMenu right >
          <DropdownItem key={1} onClick={() => this.deleteOption(this.props.id)}>                       
            Delete 
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

// type checking
WorkflowContextMenu.propTypes = {
  id: React.PropTypes.number,  
};

