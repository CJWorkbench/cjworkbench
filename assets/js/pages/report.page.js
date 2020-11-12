import { createStore, applyMiddleware, compose } from 'redux'
import errorMiddleware from '../error-middleware'
import UnhandledErrorReport from '../UnhandledErrorReport'
import React from 'react'
import ReactDOM from 'react-dom'
import { workflowReducer, applyDeltaAction } from '../workflow-reducer'
import Table from '../Report/Table'
import WorkflowWebsocket from '../WorkflowWebsocket'
import { Provider } from 'react-redux'
import { InternationalizedPage } from '../i18n/InternationalizedPage'

__webpack_public_path__ = window.STATIC_URL + 'bundles/' // eslint-disable-line

// --- Main ----
const websocket = new WorkflowWebsocket(
  window.initState.workflow.id,
  delta => store.dispatch(applyDeltaAction(delta))
)
websocket.connect()

const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose
const store = createStore(
  workflowReducer,
  window.initState,
  composeEnhancers(applyMiddleware(errorMiddleware()))
)

const tables = document.querySelectorAll('.data-table[data-step-slug]')
Array.prototype.forEach.call(tables, el => {
  ReactDOM.render(
    (
      <InternationalizedPage>
        <Provider store={store}>
          <Table stepSlug={el.getAttribute('data-step-slug')} />
          <UnhandledErrorReport />
        </Provider>
      </InternationalizedPage>
    ),
    el
  )
})

// Start Intercom, if we're that sort of installation
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
