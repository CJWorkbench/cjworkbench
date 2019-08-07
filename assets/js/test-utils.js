/* globals jest */
import { createStore, applyMiddleware } from 'redux'
import thunk from 'redux-thunk'
import promiseMiddleware from 'redux-promise-middleware'
import errorMiddleware from './error-middleware'
import { workflowReducer } from './workflow-reducer'
import React from 'react'
import { shape, object } from 'prop-types'
import { mount, shallow } from 'enzyme'
import { I18nProvider } from '@lingui/react'

// Returns new mock function that returns given json. Used for mocking "get" API calls
export function jsonResponseMock (json) {
  return jest.fn().mockImplementation(() =>
    Promise.resolve(json)
  )
}

// Returns new mock function that gives an OK HTTP response. Use for mocking "set" API calls
export function okResponseMock () {
  return jsonResponseMock(null)
}

// Helper function to return a promise that resolves after all other promise mocks,
// even if they are chained like Promise.resolve().then(...).then(...)
// Technically: this is designed to resolve on the next macrotask
// https://stackoverflow.com/questions/25915634/difference-between-microtask-and-macrotask-within-an-event-loop-context
export function tick () {
  return new Promise(resolve => {
    setTimeout(resolve, 0)
  })
}

export function sleep (ms) {
  return new Promise(resolve => {
    setTimeout(resolve, ms)
  })
}

/**
 * Return `[ notify, promise ]`; `promise` completes when `notify` is called.
 *
 * Usage:
 *
 *     const [ notify, condition ] = createConditionVariable
 *     const done = condition.then(do_something)
 *     await Promise.all([sleep(0.1).then(notify), done])
 */
export function createConditionVariable () {
  let notify
  const promise = new Promise(resolve => { notify = resolve })
  return [notify, promise]
}

/**
 * Mock Redux store with in-production reducers.
 *
 * This is for integration-style tests: they test the reducer _and_ the caller
 * at the same time.
 *
 * Usage:
 *
 *     const api = { undo: jest.fn() }
 *     const store = mockStoreWithReducer({'workflow': ..., ...}, api)
 *     store.dispatch(Actions.undo())
 *     expect(api.undo).toHaveBeenCalled()
 *     expect(store.getState().workflow).toEqual(...)
 */
export function mockStore (initialState, api = {}) {
  const middlewares = [errorMiddleware(), promiseMiddleware, thunk.withExtraArgument(api)]
  const store = createStore(workflowReducer, initialState, applyMiddleware(...middlewares))
  return store
}

/*
 * Below lie utils for testing with i18n (see https://lingui.js.org/guides/testing.html)
 */
// Create the I18nProvider to retrieve context for wrapping around.
const language = 'en'
const intlProvider = new I18nProvider({
  language,
  catalogs: {
    [language]: {}
  }
}, {})

const {
  linguiPublisher: {
    i18n: originalI18n
  }
} = intlProvider.getChildContext()

// You customize the i18n object here:
const i18n = {
  ...originalI18n,
  _: key => key // provide _ macro, for just passing down the key
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
export function shallowWithIntl (node, { context } = {}) {
  return shallow(
    nodeWithI18nProp(node),
    {
      context: Object.assign({}, context, { i18n })
    }
  )
}

export function mountWithIntl (node, { context, childContextTypes } = {}) {
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
