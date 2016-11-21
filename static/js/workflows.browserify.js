import React from 'react';
import ReactDOM from 'react-dom';

var TestApp = React.createClass({
  render: function() {
    return (
      <div className="page">
        <h1>Workflows!</h1>
      </div>
    );
  }
});

ReactDOM.render(
  React.createElement(TestApp, null),
  document.getElementById('root')
);
