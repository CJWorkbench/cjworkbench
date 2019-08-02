import React from 'react'
import { I18nProvider } from '@lingui/react'
import fetchCatalog from './catalogs'

export class I18nLoader extends React.Component {
  state = {
    catalogs: {},
  }
  
  loadCatalog = (language) => {
      this.setState(state => ({
          catalogs: {
            ...state.catalogs,
            [language]: fetchCatalog(language)
          }
      }))
  }
  
  componentDidMount() {
    this.loadCatalog(this.props.language)
  }

  shouldComponentUpdate(nextProps, nextState) {
    const { language } = nextProps
    const { catalogs } = nextState

    if (language !== this.props.language && !catalogs[language]) {
      this.loadCatalog(language)
      return false
    }

    return true
  }

  render () {
    const { children, language } = this.props
    const { catalogs } = this.state

    // Skip rendering when catalog isn't loaded.
    if (!catalogs[language]) {
        return null
    }

    return (
      <I18nProvider language={language} catalogs={catalogs}>
        {children}
      </I18nProvider>
    )
  }
}
