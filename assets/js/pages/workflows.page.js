import ReactDOM from 'react-dom'
import Workflows from '../Workflows'
import WorkbenchAPI from '../WorkbenchAPI'
import InternationalizedPage from '../i18n/InternationalizedPage'

const api = new WorkbenchAPI(null) // no websocket
const { workflows, loggedInUser } = window.initState

ReactDOM.render(
  <InternationalizedPage>
    <Workflows
      api={api}
      workflows={workflows}
      user={loggedInUser}
      currentPath={window.location.pathname}
    />
  </InternationalizedPage>,
  document.getElementById('root')
)
