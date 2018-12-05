// workflow.page.js - the master JavaScript for /workflows/:id
__webpack_public_path__ = window.STATIC_URL + 'bundles/'

import React from 'react'
import ReactDOM from 'react-dom'
import { Provider } from 'react-redux'
import * as Actions from '../workflow-reducer'
import Workflow from '../Workflow'
import api from '../WorkbenchAPI'

function launchWebsocket () {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const workflowId = window.initState.workflowId
  const url = `${protocol}//${window.location.host}/workflows/${workflowId}`
  let nSuccessfulOpens = 0

  function onOpen (ev) {
    nSuccessfulOpens += 1
    if (nSuccessfulOpens === 1) {
      Actions.store.dispatch(Actions.reloadWorkflowAction())
    } else {
      console.log('Websocket reconnected')
    }
  }

  function onMessage (ev) {
    const data = JSON.parse(ev.data)
    if ('type' in data) {
      switch (data.type) {
        case 'apply-delta':
          Actions.store.dispatch(Actions.applyDeltaAction(data.data))
          return
        case 'wfmodule-status':
          Actions.store.dispatch(
            Actions.setWfModuleStatusAction(
              data.id,
              data.status,
              data.error_msg ? data.error_msg : ''
            ))
          return
        case 'reload-workflow':
          Actions.store.dispatch(Actions.reloadWorkflowAction())
          return
        default:
          console.error('Unhandled websocket message', data)
      }
    }
  }

  function onError (ev) {
    // ignore: errors during connection are usually logged by browsers anyway;
    // other errors will cause onClose, leading to reconnect.
  }

  function onClose (_ev) {
    console.log('Websocket closed. Reconnecting in 1s')
    setTimeout(connect, 1000)
  }

  function connect () {
    const socket = new window.WebSocket(url)
    socket.onopen = onOpen
    socket.onmessage = onMessage
    socket.onclose = onClose
    socket.onerror = onError
  }

  connect()
}

launchWebsocket()

// --- Main ----

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
