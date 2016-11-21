import React from 'react';
import ReactDOM from 'react-dom';

var TestApp = React.createClass({

  getInitialState: function() {
    return {
      workflows: []
    }
  },

  componentDidMount: function() {
    var _this = this;
    fetch('/api/workflows.json')
      .then(response => response.json())
      .then(json => {
        _this.setState({workflows: json})
      })
  },

  render: function() {
    return (
      <div className="page">
        <h1>Workflows!</h1>
        <ul>
          {this.state.workflows.map(function(listValue){
            return <li key={listValue.id}>{listValue.name}</li>;
          })}
        </ul>
      </div>
    );
  }
});

ReactDOM.render(
  React.createElement(TestApp, null),
  document.getElementById('root')
);
