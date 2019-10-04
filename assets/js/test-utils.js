/* globals jest */
import { createStore, applyMiddleware } from 'redux'
import thunk from 'redux-thunk'
import promiseMiddleware from 'redux-promise-middleware'
import errorMiddleware from './error-middleware'
import { workflowReducer } from './workflow-reducer'

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
