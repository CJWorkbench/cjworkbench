// Elements of /workflows. Navbar plus a list

import React from 'react'
import { WorkflowListNavBar } from './navbar'
import WfContextMenu from './WfContextMenu'
import WorkflowMetadata from './WorkflowMetadata'
import PropTypes from 'prop-types'
import { goToUrl, logUserEvent } from "./utils";

export default class Workflows extends React.Component {
  constructor(props) {
    super(props);
    this.click = this.click.bind(this);
    this.deleteWorkflow = this.deleteWorkflow.bind(this);
    this.duplicateWorkflow = this.duplicateWorkflow.bind(this);
    this.state = { workflows: []}
  }

  // Make a new workflow when button clicked, and navigate to its Module List page
  click(e) {
    this.props.api.newWorkflow('New Workflow')
    .then(json => {
      // navigate to new WF page
      goToUrl('/workflows/' + json.id);
    })
  }

  // Ask the user if they really wanna do this. If sure, post DELETE to server
  deleteWorkflow(id) {
    if (!confirm("Permanently delete this workflow?"))
      return;

    this.props.api.deleteWorkflow(id)
    .then(response => {
      var workflowsMinusID = this.state.workflows.filter(wf => wf.id != id);
      this.setState({workflows: workflowsMinusID})
    })
  }

  duplicateWorkflow(id) {
    this.props.api.duplicateWorkflow(id)
    .then(json => {
      // Add to beginning of list because wf list is reverse chron
      var workflowsPlusDup = this.state.workflows.slice();
      workflowsPlusDup.unshift(json);
      this.setState({workflows: workflowsPlusDup})
    })
  }

  componentDidMount() {
    this.props.api.listWorkflows()
    .then(json => {
      this.setState({workflows: json})
    })
  }

  render() {
    return (
      <div className="workflows-page">
        <WorkflowListNavBar/>
        <div className="container">
          <div className="d-flex justify-content-center">
            <div className='button-blue action-button new-workflow-button' onClick={this.click}>New</div>
          </div>
          <div className="mx-auto workflows-list">
            <h3 className="workflows-list--title title-3 t-m-gray">WORKFLOWS</h3>
            <div className="workflows-item--wrap">
              {this.state.workflows.map( workflow => {
                return (
                    <a href={"/workflows/" + workflow.id} className="workflow-item"key={workflow.id}>
                        <div className='mt-1'>
                          <div className='t-d-gray mb-2 title-4'>{workflow.name}</div>

                            <WorkflowMetadata
                              workflow={workflow}
                              api={this.props.api}
                              isPublic={workflow.public}
                              inWorkflowList
                            />
                          </div>
                        
                        <div onClick={(e) => e.preventDefault()} className='menu-test-class'>
                          <WfContextMenu
                            duplicateWorkflow={ () => this.duplicateWorkflow(workflow.id) }
                            deleteWorkflow={ () => this.deleteWorkflow(workflow.id) }
                          />
                        </div>
                    </a>
                  );
                })}
            </div>
          </div>
        </div>
        <div className='help-container'>
          <a target="_blank" href="http://help.cjworkbench.org/getting-started/build-your-first-workflow" className=''>
            <div className='help-shortcut btn'>
              <div className='icon-knowledge' />
            </div>
          </a>
        </div>
      </div>
    );
  }
}

Workflows.propTypes = {
  api:        PropTypes.object.isRequired
};
