import * as React from 'react'
import PropTypes from 'prop-types'
import { withI18n } from '@lingui/react'
import { supportedLocales, supportedLocaleIds, setLocale } from './locales'

// LocaleSwitcher uses window.i18nConfig, which is injected by django in the base template
class LocaleSwitcher extends React.Component {
  static propTypes = {
    // i18n is an object injected by withI18n of lingui
    i18n: PropTypes.shape({
      language: PropTypes.oneOf(supportedLocaleIds),
      _: PropTypes.func.isRequired
    })
  }

  render () {
    if (window.i18nConfig && window.i18nConfig.showSwitcher) {
      return (
        <select defaultValue={this.props.i18n.language}>
          {supportedLocaleIds.map((locale) => (
            <option key={locale} onClick={() => setLocale(locale)} value={locale}>
              {this.props.i18n._(supportedLocales[locale])}
            </option>
          ))}
        </select>
      )
    } else {
      return null
    }
  }
}

export default withI18n()(LocaleSwitcher)
