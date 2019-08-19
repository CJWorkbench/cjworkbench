/* global describe, it, expect */
import { currentLocale, supportedLocales } from './locales'

describe('i18n helpers', () => {
  describe('currentLocale', () => {
    it('should always be defined', () => {
      expect(currentLocale).toBeDefined()
    })

    it('should be supported', () => {
      expect(Object.keys(supportedLocales)).toContain(currentLocale)
    })
  })
})
