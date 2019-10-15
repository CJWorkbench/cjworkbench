import * as React from 'react'
import PropTypes from 'prop-types'
import { withI18n } from '@lingui/react'
import { supportedLocales, supportedLocaleIds } from './locales'
import { csrfToken } from '../utils'

/**
 * A menu for the user to select a locale.
 *
 * Uses window.i18nConfig, which is injected by Django in the base template
 */
const LocaleSwitcher = React.memo(function LocaleSwitcher ({ i18n }) {
  const onChangeLocale = React.useCallback(ev => {
    ev.target.form.submit()
  })

  if (window.i18nConfig && window.i18nConfig.showSwitcher) {
    return (
      <form method='POST' action='/locale'>
        <input type='hidden' name='next' value={window.location.href} />
        <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken} />
        <select value={i18n.language} name='new_locale' onChange={onChangeLocale}>
          {supportedLocaleIds.map((locale) => (
            <option key={locale} value={locale}>
              {i18n._(supportedLocales[locale])}
            </option>
          ))}
        </select>
      </form>
    )
  } else {
    return null
  }
})
LocaleSwitcher.propTypes = {
  i18n: PropTypes.shape({
    // i18n object injected by LinguiJS withI18n()
    language: PropTypes.oneOf(supportedLocaleIds),
    _: PropTypes.func.isRequired
  })
}

export default withI18n()(LocaleSwitcher)
