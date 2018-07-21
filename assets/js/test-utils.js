import { Provider } from 'react-redux'
import React from 'react'
import { shallow } from 'enzyme'


// --- Mock API responses ---

export function mockResponse (status, statusText, response) {
  return new window.Response(response, {
    status: status,
    statusText: statusText,
    headers: {
      'Content-type': 'application/json'
    }
  });
};

// Returns new mock function that returns given json. Used for mocking "get" API calls
export function jsonResponseMock (json) {
  return jest.fn().mockImplementation(()=>
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
export function tick() {
  return new Promise(resolve => {
    setTimeout(resolve, 0);
  })
}


/**
 * Like enzyme's `shallow()`, but child components that depend on redux
 * don't crash the mount.
 *
 * See https://github.com/airbnb/enzyme/issues/472
 */
export function shallowWithStubbedStore(component) {
  const stub = () => ({})
  const store = { getState: stub, subscribe: stub, dispatch: stub }
  return shallow(<Provider store={store}>{component}</Provider>).dive()
}

