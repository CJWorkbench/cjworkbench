/* global describe, it, expect */
import { currentLocaleId, supportedLocaleIds } from './locales'

describe('i18n helpers', () => {
  describe('currentLocaleId', () => {
    it('should always be defined', () => {
      expect(currentLocaleId).toBeDefined()
    })

    it('should be supported', () => {
      expect(supportedLocaleIds).toContain(currentLocaleId)
    })
  })
})
