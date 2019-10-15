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
 * Ask the server to change the current locale and go to the page instructed
 */
export function setLocale (locale) {
  const form = document.createElement('form')
  form.action = '/locale'
  form.method = 'POST'

  const csrf = document.createElement('input')
  csrf.type = 'hidden'
  csrf.name = 'csrfmiddlewaretoken'
  csrf.value = csrfToken
  form.appendChild(csrf)

  const newLocale = document.createElement('input')
  newLocale.type = 'hidden'
  newLocale.name = 'new_locale'
  newLocale.value = locale
  form.appendChild(newLocale)

  const next = document.createElement('input')
  next.type = 'hidden'
  next.name = 'next'
  next.value = window.location
  form.appendChild(next)

  document.body.appendChild(form)
  form.submit()
}
