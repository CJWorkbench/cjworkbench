import { t } from '@lingui/macro'
import { csrfToken } from '../utils'

const supportedLocales = {
  en: t`English`,
  el: t`Greek`
}

const defaultLocale = 'en'

const currentLocale = window.i18n && window.i18n.locale && isSupported(window.i18n.locale) ? window.i18n.locale : defaultLocale

function isSupported (locale) {
  return supportedLocales.hasOwnProperty(locale)
}

/**
 * This function tries to change locale by reloading the page and adding a locale query parameter
 */
function setLocaleWithQueryParameter (locale) {
  if (isSupported(locale)) {
    window.location += (window.location.search ? '&' : '?') + `locale=${locale}` // very quick and dirty solution for reloading with added parameter
  }
}

/**
 * This function tries to change locale by sending a POST request to the server, in Django fashion
 */
function setLocaleWithPostRequest (locale) {
  if (isSupported(locale)) {
    fetch('/i18n/setlang/', {
      method: 'POST',
      body: JSON.stringify({
        language: locale
      }),
      redirect: 'follow',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json'
      }
    })
  }
}

export { supportedLocales, defaultLocale, currentLocale, setLocaleWithQueryParameter as setLocale, isSupported as isSupportedLocale }
