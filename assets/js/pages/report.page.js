import { createStore, applyMiddleware, compose } from 'redux'
import errorMiddleware from '../error-middleware'
import UnhandledErrorReport from '../UnhandledErrorReport'
import ReactDOM from 'react-dom'
import { workflowReducer, applyDeltaAction } from '../workflow-reducer'
import Table from '../Report/Table'
import WorkflowWebsocket from '../WorkflowWebsocket'
import { Provider } from 'react-redux'
import InternationalizedPage from '../i18n/InternationalizedPage'
import selectWorkflowIdOrSecretId from '../selectors/selectWorkflowIdOrSecretId'

const workflowIdOrSecretId = selectWorkflowIdOrSecretId(window.initState) // TODO select dynamically in WorkbenchAPI?
const websocket = new WorkflowWebsocket(
  workflowIdOrSecretId,
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
    <InternationalizedPage>
      <Provider store={store}>
        <Table workflowIdOrSecretId={workflowIdOrSecretId} stepSlug={el.getAttribute('data-step-slug')} />
        <UnhandledErrorReport />
      </Provider>
    </InternationalizedPage>,
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
