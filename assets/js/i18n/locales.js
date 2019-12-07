
export const supportedLocalesData = window && window.i18nConfig && window.i18nConfig.localesData ? window.i18nConfig.localesData : [
  { locale_id: 'en', locale_name: 'English' }
]

export const supportedLocaleIds = supportedLocalesData.map(localeData => localeData.locale_id)

const defaultLocale = 'en'

export const currentLocale = window.i18nConfig && window.i18nConfig.locale && isSupported(window.i18nConfig.locale) ? window.i18nConfig.locale : defaultLocale

function isSupported (locale) {
  return supportedLocaleIds.includes(locale)
}
