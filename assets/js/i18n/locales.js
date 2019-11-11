import { t } from '@lingui/macro'

export const supportedLocales = {
  en: t('js.i18n.locales.en')`English`,
  el: t('js.i18n.locales.el')`Greek`
}

export const supportedLocaleIds = Object.keys(supportedLocales)

const defaultLocale = 'en'

export const currentLocale = window.i18nConfig && window.i18nConfig.locale && isSupported(window.i18nConfig.locale) ? window.i18nConfig.locale : defaultLocale

function isSupported (locale) {
  return Object.prototype.hasOwnProperty.call(supportedLocales, locale)
}
