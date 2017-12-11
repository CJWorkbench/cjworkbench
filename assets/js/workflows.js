// Elements of /workflows. Navbar plus a list

import React from 'react'
import { WorkflowListNavBar } from './navbar'
import WfContextMenu from './WfContextMenu'
import WorkflowMetadata from './WorkflowMetadata'
import PropTypes from 'prop-types'
import { goToUrl } from "./utils";

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
      <div>
        <WorkflowListNavBar/>

        <div className="container workflows-container">

          <div className="row justify-content-md-center">
            <div className="col col-lg-2"></div>
            <div className="col-12 col-md-auto">
              <div className="input-group">
                <span className="input-group-btn">
                  <div className='button-blue action-button new-workflow-button' onClick={this.click}>New</div>
                </span>
              </div>
            </div>
            <div className="col col-lg-2"></div>
          </div>

          <div className="card w-75 mx-auto workflows-list" style={{backgroundColor:"#f6f6f6"}}>
            <div className="card-block">

              <h3 className="card-title title-3 t-m-gray workflows-card-title">WORKFLOWS</h3>

              <div className="workflows-sub-list">
                {this.state.workflows.map( workflow => {
                  return (
                      <a href={"/workflows/" + workflow.id} className="workflow-link workflow-in-list"key={workflow.id}>
                          <div className='mt-1'>
                            <div className='t-d-gray mb-2 title-4'>{workflow.name}</div>
                            <div className='wf-id-meta' onClick={(e) => e.preventDefault()}>
                              <WorkflowMetadata
                                workflow={workflow}
                                api={this.props.api}
                                isPublic={workflow.public}
                                inWorkflowList
                              />
                            </div>
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
        </div>
      </div>
    );
  }
}

Workflows.propTypes = {
  api:        PropTypes.object.isRequired
};
