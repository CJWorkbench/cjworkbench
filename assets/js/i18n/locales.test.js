/* global describe, it, expect */
import { currentLocale, supportedLocales } from './locales'

describe('i18n helpers', () => {
  it('there is a always a current locale', () => {
    expect(currentLocale).toBeDefined()
  })

  it('the current locale is supported', () => {
    expect(Object.keys(supportedLocales)).toContain(currentLocale)
  })
})
