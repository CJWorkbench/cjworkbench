// workflow.page.js - the master JavaScript for /workflows/:id
import { createStore, applyMiddleware, compose } from 'redux'
import thunk from 'redux-thunk'
import promiseMiddleware from 'redux-promise-middleware'
import errorMiddleware from '../error-middleware'
import UnhandledErrorReport from '../UnhandledErrorReport'
import React from 'react'
import ReactDOM from 'react-dom'
import { workflowReducer, applyDeltaAction } from '../workflow-reducer'
import Workflow from '../Workflow'
import WorkflowWebsocket from '../WorkflowWebsocket'
import WorkbenchAPI from '../WorkbenchAPI'
import { InternationalizedPage } from '../i18n/InternationalizedPage'

//TODO: is this line needed? we have the info in webpack config, since it is nedded in dynamically fetching localization files
__webpack_public_path__ = window.STATIC_URL + 'bundles/' // eslint-disable-line

// --- Main ----
const websocket = new WorkflowWebsocket(
  window.initState.workflow.id,
  delta => store.dispatch(applyDeltaAction(delta))
)
websocket.connect()

const api = new WorkbenchAPI(websocket)

const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose

const middlewares = [errorMiddleware(), promiseMiddleware, thunk.withExtraArgument(api)]

const store = createStore(
  workflowReducer,
  {
    ...window.initState,
    selectedPane: {
      pane: 'tab',
      tabSlug: window.initState.workflow.tab_slugs[window.initState.workflow.selected_tab_position]
    }
  },
  composeEnhancers(applyMiddleware(...middlewares))
)

// Render with Provider to root so all objects in the React DOM can access state
ReactDOM.render(
  (
    <InternationalizedPage store={store}>
        <Workflow api={api} lesson={window.initState.lessonData} />
        <UnhandledErrorReport />
    </InternationalizedPage>
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
