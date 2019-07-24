import React from 'react'
import ReactDOM from 'react-dom'
import Navbar from '../Workflows/Navbar'
import { I18nProvider } from '@lingui/react'
import { catalogs } from '../Internationalization/catalogs'
import { defaultLocale } from '../Internationalization/locales'

ReactDOM.render(
  (
    <I18nProvider language={defaultLocale} catalogs={catalogs}>
      <Navbar />
    </I18nProvider>
  ),
  document.querySelector('.navbar-wrapper')
)
