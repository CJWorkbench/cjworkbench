/* global describe, it, expect */
import { supportedLocales } from './locales'
import fetchCatalog from './catalogs'

describe('Translation catalogs', () => {
  it.each(Object.keys(supportedLocales))('fetches a valid catalog for all supported locales', (locale) => {
    const catalog = fetchCatalog(locale)
    expect(catalog).toBeDefined()
    expect(catalog.messages).toBeDefined()
    expect(Object.keys(catalog.messages)).not.toHaveLength(0)
    expect(catalog.languageData).toBeDefined()
  })
})
