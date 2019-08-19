import { t } from '@lingui/macro'

export const supportedLocales = {
  en: t('locales.en')`English`,
  el: t('locales.el')`Greek`
}

export const defaultLocale = 'en'

export const currentLocale = window.i18n && window.i18n.locale && isSupported(window.i18n.locale) ? window.i18n.locale : defaultLocale

function isSupported (locale) {
  return Object.prototype.hasOwnProperty.call(supportedLocales, locale)
}

/**
 * Change locale by reloading the page and adding a locale query parameter
 */
export function setLocale (locale) {
  if (isSupported(locale)) {
    window.location += (window.location.search ? '&' : '?') + `locale=${locale}` // very quick and dirty solution for reloading with added parameter
  }
}
