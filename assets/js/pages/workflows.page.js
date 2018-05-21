// workflow.page.js - the master JavaScript for /workflows
import React from 'react'
import ReactDOM from 'react-dom'
import Workflows from '../workflows'
import workbenchAPI from '../WorkbenchAPI'

// Global API object, encapsulates all calls to the server
const api = workbenchAPI();

ReactDOM.render(
    <Workflows api={api}/>,
    document.getElementById('root')
);

// Start Intercom, if we're that sort of installation
if (window.APP_ID) {
  window.Intercom("boot", {
    app_id: window.APP_ID,
    email: window.initState.loggedInUser.email,
    user_id: window.initState.loggedInUser.id,
    alignment: 'right',
    horizontal_padding: 20,
    vertical_padding: 20
  });
}
