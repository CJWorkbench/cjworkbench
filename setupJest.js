// https://github.com/facebook/jest/issues/6121#issuecomment-529591574
import { format } from 'util'
import Enzyme from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'

import AbortController from 'abort-controller'

import '@testing-library/jest-dom'

Enzyme.configure({ adapter: new Adapter() })

global.AbortController = AbortController

const LoggedToConsoleError = Error

const originalError = global.console.error
global.console.error = function thisTestFailsBecauseItCallsConsoleError (...args) {
  originalError(...args)
  throw new LoggedToConsoleError(format(...args))
}

const originalWarn = global.console.warn
global.console.warn = function thisTestFailsBecauseItCallsConsoleWarn (...args) {
  originalWarn(...args)
  if (/\b(componentWillMount|componentWillReceiveProps)\b/.test(args[0]) && /\bCanvas\b/.test(args[1])) {
    // TODO nix react-data-grid and its obsolete lifecycle method calls
    return // allow warnings -- for now!
  }
  throw new LoggedToConsoleError(format(...args))
}
