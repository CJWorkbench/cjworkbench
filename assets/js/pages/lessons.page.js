import React from 'react'
import ReactDOM from 'react-dom'
import Navbar from '../Workflows/Navbar'
import { InternationalizedPage } from '../i18n/InternationalizedPage'

ReactDOM.render(
  (
    <InternationalizedPage>
      <Navbar />
    </InternationalizedPage>
  ),
  document.querySelector('.navbar-wrapper')
)
