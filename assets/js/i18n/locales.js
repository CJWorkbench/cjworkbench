import { t } from '@lingui/macro'

export const supportedLocales = {
  en: t('locales.en')`English`,
  el: t('locales.el')`Greek`
}

const defaultLocale = 'en'

export const currentLocale = window.i18n && window.i18n.locale && isSupported(window.i18n.locale) ? window.i18n.locale : defaultLocale

function isSupported (locale) {
  return Object.prototype.hasOwnProperty.call(supportedLocales, locale)
}

/**
 * Reload the page, adding a "locale" query parameter to the URL
 */
export function setLocale (locale) {
  if (isSupported(locale)) {
    window.location += (window.location.search ? '&' : '?') + `locale=${locale}` // very quick and dirty solution for reloading with added parameter
  }
}
