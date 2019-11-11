import { I18nProvider } from '@lingui/react'
import React from 'react'
import { shape, object } from 'prop-types'
import { mount, shallow } from 'enzyme'

/*
 * Below lie utils for testing with i18n.
 * See https://lingui.js.org/guides/testing.html
 */
// Create the I18nProvider to retrieve context for wrapping around.
const intlProvider = new I18nProvider({
  language: 'en',
  catalogs: {
    en: {}
  }
}, {})

const {
  linguiPublisher: {
    i18n: originalI18n
  }
} = intlProvider.getChildContext()

// You customize the i18n object here:
export const i18n = {
  ...originalI18n,
  // provide _ macro, for trying to unwrap default/id or just passing down the key
  _: key => {
    if (typeof key.defaults === 'string') return key.defaults
    if (typeof key.id === 'string') return key.id
    return key
  }
}

/**
 * When using Lingui `withI18n` on components, props.i18n is required.
 */
function nodeWithI18nProp (node) {
  return React.cloneElement(node, { i18n })
}

/*
 * Methods to use
 */
export function shallowWithI18n (node, { context } = {}) {
  return shallow(
    nodeWithI18nProp(node),
    {
      context: Object.assign({}, context, { i18n })
    }
  )
}

export function mountWithI18n (node, { context, childContextTypes } = {}) {
  const newContext = Object.assign({}, context, { linguiPublisher: { i18n } })
  /*
   * I18nProvider sets the linguiPublisher in the context for withI18n to get
   * the i18n object from.
   */
  const newChildContextTypes = Object.assign({},
    {
      linguiPublisher: shape({
        i18n: object.isRequired
      }).isRequired
    },
    childContextTypes
  )
  return mount(
    nodeWithI18nProp(node),
    {
      context: newContext,
      childContextTypes: newChildContextTypes
    }
  )
}
