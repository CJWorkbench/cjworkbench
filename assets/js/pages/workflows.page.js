import ReactDOM from 'react-dom'
import Workflows from '../Workflows'
import WorkbenchAPI from '../WorkbenchAPI'
import InternationalizedPage from '../i18n/InternationalizedPage'

const api = new WorkbenchAPI(null) // no websocket
const { workflows, loggedInUser } = window.initState

ReactDOM.render((
  <InternationalizedPage>
    <Workflows
      api={api}
      workflows={workflows}
      user={loggedInUser}
      currentPath={window.location.pathname}
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
