
export const supportedLocalesData = window && window.i18nConfig && window.i18nConfig.localesData ? window.i18nConfig.localesData : [
  { id: 'en', name: 'English' }
]

export const supportedLocaleIds = supportedLocalesData.map(localeData => localeData.id)

const defaultLocale = 'en'

export const currentLocale = window.i18nConfig && window.i18nConfig.locale && isSupported(window.i18nConfig.locale) ? window.i18nConfig.locale : defaultLocale

function isSupported (locale) {
  return supportedLocaleIds.includes(locale)
}
