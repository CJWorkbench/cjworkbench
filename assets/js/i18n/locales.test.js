/* global describe, it, expect */
import { currentLocale, supportedLocaleIds } from './locales'

describe('i18n helpers', () => {
  describe('currentLocale', () => {
    it('should always be defined', () => {
      expect(currentLocale).toBeDefined()
    })

    it('should be supported', () => {
      expect(supportedLocaleIds).toContain(currentLocale)
    })
  })
})
