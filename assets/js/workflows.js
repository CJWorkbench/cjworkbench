// Elements of /workflows. Navbar plus a list

import React from 'react';
import { NavBar } from './navbar';
import { csrfToken, goToUrl } from './utils'

export default class Workflows extends React.Component {
  constructor(props) {
    super(props);
    this.click = this.click.bind(this);
    this.deleteWorkflow= this.deleteWorkflow.bind(this);
    this.state = { workflows: []}
  }

  // Make a new workflow when button clicked
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
        <NavBar/>

        <div className="container">

          <div className="row justify-content-md-center some-margin">
            <div className="col col-lg-2"></div>
            <div className="col-12 col-md-auto">
              <div className="input-group">
                <span className="input-group-btn">
                  <button className='new-workflow-button btn btn-secondary' onClick={this.click}>New</button>
                </span>
              </div>
            </div>
            <div className="col col-lg-2"></div>
          </div>

          <div className="card w-75 mx-auto">
            <div className="card-block">

              <h3 className="card-title some-margin">Workflows</h3>

              <div className="some-margin">
                {this.state.workflows.map( listValue => {
                  return (
                      <div className="card card-block some-margin item-test-class" key={listValue.id}>
                        <div className='d-flex justify-content-between'>
                          <a href={"/workflows/" + listValue.id}>{listValue.name}</a>
                          <button type='button' className='btn btn-secondary btn-sm button-test-class' onClick={() => this.deleteWorkflow(listValue.id)} >&times;</button>
                        </div>
                        <div className='d-flex align-items-start'>
                          <div>Source: Placeholder - </div>
                          <div>Updated: Placeholder - </div>
                          <div>Public</div>                          
                        </div>
                      </div>
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

