import ReactDOM from 'react-dom'
import PlanPage from '../settings/PlanPage'
import WorkbenchAPI from '../WorkbenchAPI'
import InternationalizedPage from '../i18n/InternationalizedPage'

const api = new WorkbenchAPI(null) // no websocket
const { user, products } = window.initState

ReactDOM.render(
  <InternationalizedPage>
    <PlanPage api={api} user={user} products={products} />
  </InternationalizedPage>,
  document.getElementById('root')
)
