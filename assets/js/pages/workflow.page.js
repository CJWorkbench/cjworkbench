// workflow.page.js - the master JavaScript for /workflows/:id
__webpack_public_path__ = window.STATIC_URL + 'bundles/'

import React from 'react'
import ReactDOM from 'react-dom'
import { Provider } from 'react-redux'
import * as Actions from '../workflow-reducer'
import Workflow from '../Workflow'
import api from '../WorkbenchAPI'

// --- Main ----
const websocket = WorkflowWebsocket(window.initState.workflow.id, Actions.store)
websocket.connect()

// Render with Provider to root so all objects in the React DOM can access state
ReactDOM.render(
  (
    <Provider store={Actions.store}>
      <Workflow api={api} lesson={window.initState.lessonData} />
    </Provider>
  ),
  document.getElementById('root')
)

// Start Intercom, if we're that sort of installation
// We are indeed: Very mission, much business!
if (window.APP_ID) {
  if (window.initState.loggedInUser) {
    window.Intercom('boot', {
      app_id: window.APP_ID,
      email: window.initState.loggedInUser.email,
      user_id: window.initState.loggedInUser.id,
      alignment: 'right',
      horizontal_padding: 30,
      vertical_padding: 20
    })
  } else {
    // no one logged in -- viewing read only workflow
    window.Intercom('boot', {
      app_id: window.APP_ID,
      alignment: 'right',
      horizontal_padding: 30,
      vertical_padding: 20
    })
  }
}
