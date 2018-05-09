import { Provider } from 'react-redux'
import React from 'react'
import { shallow } from 'enzyme'

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
