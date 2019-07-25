import React from 'react'
import { connect } from 'react-redux'
import { I18nProvider } from '@lingui/react'
import fetchCatalog from './catalogs'
import { defaultLocale } from './locales'

class I18nLoaderClass extends React.Component {
  state = {
    catalogs: {},
  }
  
  loadCatalog = (language) => {
      fetchCatalog(language)
      .then((catalog) => {
        this.setState(state => ({
          catalogs: {
            ...state.catalogs,
            [language]: catalog
          }
        }))
      })
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

const mapStateToProps = (state) => {
    return {language: state && state.locale ? state.locale : defaultLocale}
}

export const I18nLoader = connect(mapStateToProps)(I18nLoaderClass)
