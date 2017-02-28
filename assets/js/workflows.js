import React from 'react';
import ReactDOM from 'react-dom';
import { csrfToken } from './utils'

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
      <div className="page">
        <h1>Workflows!</h1>
        <ul>
          {this.state.workflows.map(function (listValue) {
            return <li key={listValue.id}><a href={"/workflows/" + listValue.id}>{listValue.name}</a></li>;
          })}
        </ul>
        <input type="text" className='newWorkflowName' value={this.state.value} onChange={this.handleTextChange}/>
        <button className='newWorkflowButton' onClick={this.click}>New</button>
      </div>
    );
  }
}

ReactDOM.render(
  React.createElement(Workflows, null),
  document.getElementById('root')
);
