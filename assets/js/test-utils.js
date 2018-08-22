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
