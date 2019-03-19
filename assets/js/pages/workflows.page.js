// workflow.page.js - the master JavaScript for /workflows
import React from 'react'
import ReactDOM from 'react-dom'
import Workflows from '../Workflows'
import WorkbenchAPI from '../WorkbenchAPI'

const api = new WorkbenchAPI(null) // no websocket

ReactDOM.render(
    <Workflows api={api} workflows={window.initState.workflows}/>,
    document.getElementById('root')
)

// Start Intercom, if we're that sort of installation
if (window.APP_ID) {
  window.Intercom("boot", {
    app_id: window.APP_ID,
    email: window.initState.loggedInUser.email,
    user_id: window.initState.loggedInUser.id,
    alignment: 'right',
    horizontal_padding: 20,
    vertical_padding: 20
  })
}
