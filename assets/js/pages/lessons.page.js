import React from 'react'
import ReactDOM from 'react-dom'
import MainNavFragment from '../Page/MainNav/MainNavFragment'
import InternationalizedPage from '../i18n/InternationalizedPage'

ReactDOM.render(
  (
    <InternationalizedPage>
      <MainNavFragment
        user={JSON.parse(window.initState || '{}').loggedInUser || null}
        currentPath={window.location.pathname}
      />
    </InternationalizedPage>
  ),
  document.querySelector('nav.main-nav')
)
