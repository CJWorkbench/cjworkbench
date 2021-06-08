import ReactDOM from 'react-dom'
import BillingPage from '../settings/BillingPage'
import WorkbenchAPI from '../WorkbenchAPI'
import InternationalizedPage from '../i18n/InternationalizedPage'

const api = new WorkbenchAPI(null) // no websocket
const { user } = window.initState

ReactDOM.render(
  <InternationalizedPage>
    <BillingPage api={api} user={user} />
  </InternationalizedPage>,
  document.getElementById('root')
)
