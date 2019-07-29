import React from 'react'
import ReactDOM from 'react-dom'
import { createStore } from 'redux'
import Navbar from '../Workflows/Navbar'
import { localeReducer } from '../i18n/actions'
import InternationalizedPage from '../i18n/InternationalizedPage'

const store = createStore(
  localeReducer
)

ReactDOM.render(
  (
    <InternationalizedPage store={store}>
      <Navbar />
    </InternationalizedPage>
  ),
  document.querySelector('.navbar-wrapper')
)
