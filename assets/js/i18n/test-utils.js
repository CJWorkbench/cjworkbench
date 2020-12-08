import React from 'react'
import { i18n } from '@lingui/core'
import { I18nProvider } from '@lingui/react'
import { render } from '@testing-library/react'
import { mount, shallow } from 'enzyme'

/*
 * Below lie utils for testing with i18n.
 * See https://lingui.js.org/guides/testing.html
 */

// You customize the i18n object here:
i18n.loadLocaleData('en', { plurals: require('make-plural/plurals').en })
i18n.load('en', {})
i18n.activate('en')

function I18nWrapper (props) {
  return <I18nProvider i18n={i18n} {...props} />
}

export function shallowWithI18n (node, options = {}) {
  return shallow(node, { wrappingComponent: I18nWrapper, ...options })
}

export function mountWithI18n (node, options = {}) {
  return mount(node, { wrappingComponent: I18nWrapper, ...options })
}

export function renderWithI18n (node, options) {
  return render(node, { wrapper: I18nWrapper, ...options })
}
