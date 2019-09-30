import { setupI18n } from "@lingui/core"
import { currentLocale } from './locales'
import { fetchCatalog } from './catalogs'

export default const i18n = setupI18n({
   language: currentLocale,
   catalogs: {
       currentLocale: fetchCatalog(currentLocale)
   }
})
