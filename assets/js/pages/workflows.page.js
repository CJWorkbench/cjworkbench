// workflow.page.js - the master JavaScript for /workflows
import React from 'react'
import ReactDOM from 'react-dom'
import { Provider } from 'react-redux'
import Workflows from '../Workflows'
import WorkbenchAPI from '../WorkbenchAPI'
import { createStore } from 'redux'
import { I18nLoader } from '../Internationalization/I18nLoader'
import { localeReducer } from '../Internationalization/actions'
import InternationalizedPage from '../Internationalization/InternationalizedPage'

const api = new WorkbenchAPI(null) // no websocket
const { workflows, loggedInUser } = window.initState

const store = createStore(
  localeReducer,
  {...window.initState}
)

ReactDOM.render((
  <InternationalizedPage store={store}>
      <Workflows
        api={api}
        workflows={workflows}
        user={loggedInUser}
      />
  </InternationalizedPage>
), document.getElementById('root'))

// Start Intercom, if we're that sort of installation
if (window.APP_ID) {
  window.Intercom('boot', {
    app_id: window.APP_ID,
    email: window.initState.loggedInUser.email,
    user_id: window.initState.loggedInUser.id,
    alignment: 'right',
    horizontal_padding: 20,
    vertical_padding: 20
  })
}
