// workflow.page.js - the master JavaScript for /workflows
import React from 'react'
import ReactDOM from 'react-dom'
import Workflows from './workflows'
import workbenchAPI from './WorkbenchAPI'

// Global API object, encapsulates all calls to the server
const api = workbenchAPI();

require('bootstrap/dist/css/bootstrap.css');
require('../css/style.css');

ReactDOM.render(
  <Workflows api={api}/>,
  document.getElementById('root')
);
