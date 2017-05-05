// workflow.page.js - the master JavaScript for /workflows
import React from 'react';
import Workflows from './workflows'

require('bootstrap/dist/css/bootstrap.css');
require('../css/style.css');

ReactDOM.render(
  React.createElement(Workflows, null),
  document.getElementById('root')
);
