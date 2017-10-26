// Elements of /workflows. Navbar plus a list

import React from 'react'
import { WorkflowListNavBar } from './navbar'
import { csrfToken, goToUrl } from './utils'
import WfContextMenu from './WfContextMenu'
import WorkflowMetadata from './WorkflowListMetadata'


export default class Workflows extends React.Component {
  constructor(props) {
    super(props);
    this.click = this.click.bind(this);
    this.deleteWorkflow = this.deleteWorkflow.bind(this);
    this.state = { workflows: []}
  }

  // Make a new workflow when button clicked, and navigate to its Module List page
  click(e) {

    fetch('/api/workflows',
      {
        method: 'post',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({name: "New Workflow"})
    })
    .then(response => response.json())
    .then(json => {
      // ID of new Workflow has been returned by this step, can navigate to new WF page
      goToUrl('/workflows/' + json.id);
    })
  }

  // Ask the user if they really wanna do this. If sure, post DELETE to server
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

  componentDidMount() {
    var _this = this;

    fetch('/api/workflows', {credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        _this.setState({workflows: json, newWorkflowName: this.state.newWorkflowName})
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
                {this.state.workflows.map( listValue => {
                  return (
                      <a href={"/workflows/" + listValue.id} className="workflow-link card card-block item-test-class workflow-in-list"key={listValue.id}>
                        <div className='my-auto d-flex justify-content-between align-items-center'>
                          <div className='wf-id-stack'>
                            <div className='wf-id-name t-d-gray title-4'>{listValue.name}</div>
                            <div className='wf-id-meta'>
                              <WorkflowMetadata
                                workflow={listValue}
                                api={this.props.api}
                                user={this.props.user}
                                isPublic={this.state.isPublic}
                              />
                            </div>
                          </div>
                          <div onClick={(e) => e.preventDefault()} className="menu-test-class">
                            <WfContextMenu deleteWorkflow={ () => this.deleteWorkflow(listValue.id) }/>
                          </div>
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
