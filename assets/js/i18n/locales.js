/* global fetch */
import { t } from '@lingui/macro'
import { csrfToken } from '../utils'

export const supportedLocales = {
  en: t('locales.en')`English`,
  el: t('locales.el')`Greek`
}

export const supportedLocaleIds = Object.keys(supportedLocales)

const defaultLocale = 'en'

export const currentLocale = window.i18nConfig && window.i18nConfig.locale && isSupported(window.i18nConfig.locale) ? window.i18nConfig.locale : defaultLocale

function isSupported (locale) {
  return Object.prototype.hasOwnProperty.call(supportedLocales, locale)
}

/**
 * Reload the page, adding a "locale" query parameter to the URL
 */
export async function setLocale (locale) {
  const response = await fetch('/i18n/set_locale', {
    method: 'POST',
    credentials: 'same-origin',
    redirect: 'follow',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
      new_locale: locale
    })
  })
  if (response.url) {
    window.location = response.url
  }
}
