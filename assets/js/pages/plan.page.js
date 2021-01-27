import React from 'react'
import ReactDOM from 'react-dom'
import PlanPage from '../settings/PlanPage'
import WorkbenchAPI from '../WorkbenchAPI'
import InternationalizedPage from '../i18n/InternationalizedPage'

const api = new WorkbenchAPI(null) // no websocket
const { user, plans } = window.initState

ReactDOM.render((
  <InternationalizedPage>
    <PlanPage api={api} user={user} plans={plans} />
  </InternationalizedPage>
), document.getElementById('root'))

// Start Intercom, if we're that sort of installation
if (window.APP_ID) {
  window.Intercom('boot', {
    app_id: window.APP_ID,
    email: window.initState.user.email,
    user_id: window.initState.user.id,
    alignment: 'right',
    horizontal_padding: 20,
    vertical_padding: 20
  })
}
