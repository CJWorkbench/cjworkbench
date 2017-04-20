import React from 'react';
import ReactDOM from 'react-dom';
import { csrfToken } from './utils'

require('bootstrap/dist/css/bootstrap.css');
require('../css/style.css');

class Workflows extends React.Component {
  constructor(props) {
    super(props);
    this.click = this.click.bind(this);
    this.handleTextChange = this.handleTextChange.bind(this);
    this.state = { workflows: [], newWorkflowName: '' }
  }

  handleTextChange(event) {
    this.setState({workflows: this.state.workflows, newWorkflowName: event.target.value});
  }

  // Make a new workflow when button clicked
  click(e) {
    fetch('/api/workflows', {
      method: 'post',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({name: this.state.newWorkflowName})
    })
    .then(response => response.json())
    .then(json => {
      var newWorkflows = this.state.workflows.slice();
      newWorkflows.push(json);
      this.setState({workflows: newWorkflows, newWorkflowName: ''})
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
      <div className="container">
        <div className="card w-75 mx-auto">
          <div className="card-block drop-shadow">

            <h3 className="card-title">Your Workflows</h3>

            <div className="some-margin">
              {this.state.workflows.map(function (listValue) {
                return (
                    <div className="card card-block some-margin" key={listValue.id}><a href={"/workflows/" + listValue.id}>{listValue.name}</a></div>
                );
              })}
            </div>

            <div className="row justify-content-md-center some-margin">
              <div className="col col-lg-2"></div>
              <div className="col-12 col-md-auto">
                <div className="input-group">
                  <input type="text" className='newWorkflowName form-control' value={this.state.value} onChange={this.handleTextChange}/>
                  <span className="input-group-btn">
                    <button className='newWorkflowButton btn btn-secondary' onClick={this.click}>New</button>
                  </span>
                </div>
              </div>
              <div className="col col-lg-2"></div>
            </div>

          </div>
        </div>
      </div>
    );
  }
}

ReactDOM.render(
  React.createElement(Workflows, null),
  document.getElementById('root')
);
