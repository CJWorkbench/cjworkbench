import React from 'react'
import ReactDOM from 'react-dom'
import { createStore } from 'redux'
import Navbar from '../Workflows/Navbar'
import { localeReducer } from '../Internationalization/actions'
import InternationalizedPage from '../Internationalization/InternationalizedPage'

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
