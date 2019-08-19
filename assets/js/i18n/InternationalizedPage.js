import React from 'react'
import { I18nProvider } from '@lingui/react'
import fetchCatalog from './catalogs'
import { currentLocale } from './locales'

export class InternationalizedPage extends React.Component {
  render () {
    const catalogs = {
      [currentLocale]: fetchCatalog(currentLocale)
    }
    return (
      <I18nProvider language={currentLocale} catalogs={catalogs}>
        {this.props.children}
      </I18nProvider>
    )
  }
}
