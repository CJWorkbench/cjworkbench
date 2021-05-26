// https://github.com/facebook/jest/issues/6121#issuecomment-529591574
import { format } from 'util'
import Enzyme from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

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
  throw new LoggedToConsoleError(format(...args))
}
