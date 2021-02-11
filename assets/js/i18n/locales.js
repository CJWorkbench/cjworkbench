const defaultLocaleId = 'en'

export const supportedLocalesData =
  window && window.i18nConfig && window.i18nConfig.localesData
    ? window.i18nConfig.localesData
    : [{ id: defaultLocaleId, name: 'English' }]

export const supportedLocaleIds = supportedLocalesData.map(
  localeData => localeData.id
)

export const currentLocaleId =
  window.i18nConfig &&
  window.i18nConfig.locale &&
  isSupported(window.i18nConfig.locale)
    ? window.i18nConfig.locale
    : defaultLocaleId

function isSupported (locale) {
  return supportedLocaleIds.includes(locale)
}
