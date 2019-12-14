import React from 'react'
import { I18nProvider } from '@lingui/react'
import fetchCatalog from './catalogs'
import { currentLocaleId } from './locales'

export class InternationalizedPage extends React.Component {
  render () {
    const catalogs = {
      [currentLocaleId]: fetchCatalog(currentLocaleId)
    }
    return (
      <I18nProvider language={currentLocaleId} catalogs={catalogs}>
        {this.props.children}
      </I18nProvider>
    )
  }
}
