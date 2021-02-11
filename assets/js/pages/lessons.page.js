import ReactDOM from 'react-dom'
import MainNavFragment from '../Page/MainNav/MainNavFragment'
import InternationalizedPage from '../i18n/InternationalizedPage'

const initState = JSON.parse(window.initState || '{}')

ReactDOM.render(
  (
    <InternationalizedPage>
      <MainNavFragment
        courses={initState.courses || null}
        currentPath={window.location.pathname}
        user={initState.loggedInUser || null}
      />
    </InternationalizedPage>
  ),
  document.querySelector('nav.main-nav')
)
