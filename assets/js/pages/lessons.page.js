import React from 'react'
import ReactDOM from 'react-dom'
import Navbar from '../Workflows/Navbar'
import InternationalizedPage from '../i18n/InternationalizedPage'
import setupI18nGlobal from '../i18n/setupI18nGlobal'

setupI18nGlobal()

ReactDOM.render(
  (
    <InternationalizedPage>
      <Navbar user={JSON.parse(window.initState || '{}').loggedInUser || null} />
    </InternationalizedPage>
  ),
  document.querySelector('.navbar-wrapper')
)
