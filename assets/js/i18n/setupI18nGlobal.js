import { i18n } from '@lingui/core'
import { en, el } from 'make-plural/plurals'
import { currentLocaleId } from './locales'
import fetchCatalog from './catalogs'

/**
 * Set up i18n, as per https://lingui.js.org/ref/core.html
 *
 * It sure feels silly as a global variable. TODO consider react-intl.
 */
export default function setupI18nGlobal () {
  const pluralRulesets = { en, el }
  i18n.loadLocaleData(currentLocaleId, { plurals: pluralRulesets[currentLocaleId] })

  const messages = fetchCatalog(currentLocaleId)
  i18n.load(currentLocaleId, messages)
  i18n.activate(currentLocaleId)
}
