/* global describe, it, expect */
import { supportedLocaleIds } from './locales'
import fetchCatalog from './catalogs'

describe('i18n helpers', () => {
  describe('message catalogs', () => {
    it.each(supportedLocaleIds)('%s should have a valid catalog', (locale) => {
      const catalog = fetchCatalog(locale)
      expect(catalog).toBeDefined()
      expect(catalog.messages).toBeDefined()
      expect(Object.keys(catalog.messages)).not.toHaveLength(0)
    })
  })
})
