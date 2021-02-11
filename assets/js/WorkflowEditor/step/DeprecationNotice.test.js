/* globals describe, it, expect */
import DeprecationNotice from './DeprecationNotice'
import { mountWithI18n } from '../../i18n/test-utils'

describe('DeprecationNotice', () => {
  const wrapper = (extraProps = {}) => {
    return mountWithI18n(
      <DeprecationNotice
        helpUrl='https://example.org'
        message='Message'
        {...extraProps}
      />
    )
  }

  it('renders a deprecation message', () => {
    const w = wrapper({ message: 'Deprecated here is a message' })
    expect(w.find('p').text()).toEqual('Deprecated here is a message')
  })

  it('renders a link', () => {
    const w = wrapper({ helpUrl: 'https://example.org', message: 'Deprecated' })
    expect(w.find('a').prop('href')).toEqual('https://example.org')
  })

  it('renders null when there is no deprecation message', () => {
    const w = wrapper({ message: null })
    expect(w.html()).toBe(null)
  })
})
