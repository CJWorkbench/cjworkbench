/* globals describe, expect, it, jest, test */
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { WorkbenchAPIContext } from '../../../WorkbenchAPI'
import { ErrorResponse } from '../../../WorkflowWebsocket'
import { act, fireEvent, render, waitForElementToBeRemoved } from '@testing-library/react'
import { I18nWrapper } from '../../../i18n/test-utils'
import { mockStore } from '../../../test-utils'
import { sleep, tick } from '../../../test-utils'
import { Provider } from 'react-redux'

const TypicalInitialProps = {
  workflowId: 1,
  stepId: 2, // TODO nix
  stepSlug: 'step-2',
  isAutofetch: false,
  fetchInterval: 86400, // 1/day
  isEmailUpdates: false,
  onClose: jest.fn(),
  trySetAutofetch: jest.fn(),
  setEmailUpdates: jest.fn(),
  delayMsAfterServerOk: 1
}

function renderWithStoreAndApi (store, api, children) {
  function Wrapper (props) {
    return (
      <I18nWrapper>
        <WorkbenchAPIContext.Provider value={api}>
          <Provider store={store}>
            {props.children}
          </Provider>
        </WorkbenchAPIContext.Provider>
      </I18nWrapper>
    )
  }

  return render(children, { wrapper: Wrapper })
}

test('User turns on fetches', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 1 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={86400}
    />
  )

  fireEvent.click(getByLabelText('OFF'))

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 86400)

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('2 of 5 updates/day') // from state

  done({}) // API responds. Redux store hasn't been updated yet; two updates remain

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('2 of 5 updates/day') // from state

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 2 } } } })

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('2 of 5 updates/day') // from state

  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400}
    />
  )

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('2 of 5 updates/day') // from state

  await waitForElementToBeRemoved(() => getByText('Saving…'))
  getByLabelText('ON') // exists
  getByText('2 of 5 updates/day') // from store
})

test('User changes update interval', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 2 }, // one on this step, one elsewhere
      limits: { fetches_per_day: 50 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400}
    />
  )

  fireEvent.change(getByLabelText('Check for updates every'), { target: { value: 3600 } })

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 3600)

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  done({}) // API responds. Redux store hasn't been updated yet; two updates remain

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 25 } } } })

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={3600}
    />
  )

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  await waitForElementToBeRemoved(() => getByText('Saving…'))
  getByLabelText('ON') // exists
  getByText('25 of 50 updates/day') // from store
})

test('User turns off fetches', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 25 }, // 24 on this step, one elsewhere
      limits: { fetches_per_day: 50 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={3600}
    />
  )

  fireEvent.click(getByLabelText('ON'))

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', false, 3600)

  getByLabelText('OFF') // exists
  getByText('Saving…')
  getByText('1 of 50 updates/day') // from state

  done({}) // API responds. Redux store hasn't been updated yet; two updates remain

  getByLabelText('OFF') // exists
  getByText('Saving…')
  getByText('1 of 50 updates/day') // from state

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 1 } } } })

  getByLabelText('OFF') // exists
  getByText('Saving…')
  getByText('1 of 50 updates/day') // from state

  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={3600}
    />
  )

  getByLabelText('OFF') // exists
  getByText('Saving…')
  getByText('1 of 50 updates/day') // from state

  await waitForElementToBeRemoved(() => getByText('Saving…'))
  getByLabelText('OFF') // exists
  getByText('1 of 50 updates/day') // from store
})

test('User has a "X days" interval', () => {
  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 100 },
      limits: { fetches_per_day: 200 },
      subscribedStripeProductIds: []
    }
  })

  const api = {}

  const { getByDisplayValue } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400 * 7}
    />
  )
  getByDisplayValue('7 days')
})

test('User has a "X hours" interval', () => {
  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 100 },
      limits: { fetches_per_day: 200 },
      subscribedStripeProductIds: []
    }
  })

  const { getByDisplayValue } = renderWithStoreAndApi(
    store,
    {},
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={3600 * 7}
    />
  )
  getByDisplayValue('7 hours')
})

test('User has a "X minutes" interval', () => {
  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 100 },
      limits: { fetches_per_day: 200 },
      subscribedStripeProductIds: []
    }
  })

  const { getByDisplayValue } = renderWithStoreAndApi(
    store,
    {},
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={1234}
    />
  )
  getByDisplayValue('20.567 minutes')
})

test('User changes update interval', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 2 }, // one on this step, one elsewhere
      limits: { fetches_per_day: 50 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400}
    />
  )

  fireEvent.change(getByLabelText('Check for updates every'), { target: { value: 3600 } })

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 3600)

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  done({}) // API responds. Redux store hasn't been updated yet; two updates remain

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 25 } } } })

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={3600}
    />
  )

  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  await waitForElementToBeRemoved(() => queryByText('Saving…'))
  getByLabelText('ON') // exists
  getByText('25 of 50 updates/day') // from store
})

test('Unpaid user tries to turn on fetches but is over limit; upgrades and then succeeds', () => {
  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 5 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: []
    }
  })

  const { baseElement, getByLabelText, getByText, queryByText, debug } = renderWithStoreAndApi(
    store,
    {},
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={86400}
    />
  )

  expect(getByLabelText('OFF').disabled).toBe(true)
  expect(baseElement.querySelector('.need-upgrade')).not.toBe(null)
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { limits: { fetches_per_day: 20 }, subscribedStripeProductIds: ['prod-1'] } } })
  expect(baseElement.querySelector('.need-upgrade')).toBe(null)
  expect(getByLabelText('OFF').disabled).toBe(false)
})

test('Unpaid user tries to select hourly but is over limit; upgrades and then succeeds', () => {
  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 5 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: []
    }
  })

  const { getByLabelText, getByText, queryByText } = renderWithStoreAndApi(
    store,
    {},
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400}
    />
  )

  const select = getByLabelText('Check for updates every')
  const option = Array.from(select.childNodes).find(o => o.value === '3600')

  expect(option.disabled).toBe(true)
  expect(option.textContent).toEqual('hour — upgrade')

  getByText('Upgrade') // There's gotta be an Upgrade button; the user will click it....
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { limits: { fetches_per_day: 1000 }, subscribedStripeProductIds: ['prod-1'] } } })
  expect(queryByText('Upgrade')).toBe(null)

  expect(option.disabled).toBe(false)
  expect(option.textContent).toEqual('hour')
})

test('Paid user tries to turn on fetches but is over limit', () => {
  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 5 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: ['prod-1']
    }
  })

  const { baseElement, getByLabelText, getByText, queryByText, debug } = renderWithStoreAndApi(
    store,
    {},
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={86400}
    />
  )

  expect(getByLabelText('OFF').disabled).toBe(true)
  expect(baseElement.querySelector('.over-limit')).not.toBe(null)
})

test('Paid user tries to select hourly but is over limit', () => {
  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 5 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: ['prod-1']
    }
  })

  const { baseElement, getByLabelText, getByText, queryByText, debug } = renderWithStoreAndApi(
    store,
    {},
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={true}
      fetchInterval={86400}
    />
  )

  const select = getByLabelText('Check for updates every')
  const option = Array.from(select.childNodes).find(o => o.value === '3600')
  expect(option.disabled).toBe(true)
  expect(option.textContent).toEqual('hour — over limit')
})

test('User over limit decreases usage', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 25 }, // 24 on this step, one elsewhere
      limits: { fetches_per_day: 10 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={3600}
    />
  )

  const select = getByLabelText('Check for updates every')
  const optionHour = Array.from(select.childNodes).find(o => o.value === '3600')
  expect(optionHour.disabled).toBe(false)

  fireEvent.change(getByLabelText('Check for updates every'), { target: { value: 86400 } })

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 86400)

  getByText('Saving…')
  getByText('2 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  done({}) // API responds. Redux store hasn't been updated yet; two updates remain

  getByText('Saving…')
  getByText('2 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 2 } } } })

  getByText('Saving…')
  getByText('2 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400}
    />
  )

  getByText('Saving…')
  getByText('2 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  await waitForElementToBeRemoved(() => queryByText('Saving…'))
  getByText('2 of 10 updates/day') // from store
  expect(optionHour.disabled).toBe(true)
})

test('User over limit decreases usage and remains over limit', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 1024 }, // 24 on this step, 1,000 elsewhere
      limits: { fetches_per_day: 10 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={3600}
    />
  )

  const select = getByLabelText('Check for updates every')
  const optionHour = Array.from(select.childNodes).find(o => o.value === '3600')
  expect(optionHour.disabled).toBe(false)

  fireEvent.change(getByLabelText('Check for updates every'), { target: { value: 86400 } })

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 86400)

  getByText('Saving…')
  getByText('1,001 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  done({}) // API responds. Redux store hasn't been updated yet; two updates remain

  getByText('Saving…')
  getByText('1,001 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 1001 } } } })

  getByText('Saving…')
  getByText('1,001 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400}
    />
  )

  getByText('Saving…')
  getByText('1,001 of 10 updates/day') // from state
  expect(optionHour.disabled).toBe(true)

  await waitForElementToBeRemoved(() => queryByText('Saving…'))
  getByText('1,001 of 10 updates/day') // from store
  expect(optionHour.disabled).toBe(true)
})

test('User over limit disables fetches', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 6 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={86400}
    />
  )

  fireEvent.click(getByLabelText('ON'))
  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', false, 86400)

  getByText('Saving…')
  getByText('5 of 5 updates/day') // from state
  expect(getByLabelText('OFF').disabled).toBe(true)

  done({}) // API responds. Redux store hasn't been updated yet; two updates remain

  getByText('Saving…')
  getByText('5 of 5 updates/day') // from state
  expect(getByLabelText('OFF').disabled).toBe(true)

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 5 } } } })

  getByText('Saving…')
  getByText('5 of 5 updates/day') // from state
  expect(getByLabelText('OFF').disabled).toBe(true)

  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={86400}
    />
  )

  getByText('Saving…')
  getByText('5 of 5 updates/day') // from state
  expect(getByLabelText('OFF').disabled).toBe(true)

  await waitForElementToBeRemoved(() => queryByText('Saving…'))
  getByText('5 of 5 updates/day') // from store
  expect(getByLabelText('OFF').disabled).toBe(true)
})

test('User over limit disables 24/day fetches, dropping below limit, and tries to turn on 1/day', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 24 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByDisplayValue, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch
      fetchInterval={3600}
    />
  )

  fireEvent.click(getByLabelText('ON'))
  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', false, 3600)

  // Do the whole API-response dance
  done({}) // API responds. Redux store hasn't been updated yet; two updates remain
  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 0 } } } })
  // The other update: the workflow changes
  rerender(
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={3600}
    />
  )
  // DO NOT wait for the timeout. Use the 'dirty' state.
  // await waitForElementToBeRemoved(() => queryByText('Saving…'))

  // Now, how does the user select "by day"?
  // We can't re-enable with fetchInterval=3600; but we _can_ re-enable with
  // fetchInterval=86400. So let's do that.
  getByDisplayValue('day')  // Since "hour" can't be selected, we render "day"
  fireEvent.click(getByLabelText('OFF'))
  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 86400)
  // ... now assume the rest of the update completes as we'd expect
})

test('User starts saving and then unplugs network; retries and it works', async () => {
  let fail
  const response = new Promise((resolve, reject) => { fail = reject })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 1 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={86400}
    />
  )

  fireEvent.click(getByLabelText('OFF'))

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 86400)
  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('2 of 5 updates/day') // from state

  await act(async () => { fail(new Error("foo")) })

  getByLabelText('ON') // exists
  getByText('2 of 5 updates/day') // from state
  await act(async () => { fireEvent.click(getByText('Retry')) })
  expect(api.trySetStepAutofetch).toHaveBeenNthCalledWith(2, 'step-2', true, 86400)
})

test('User edits but server says over-quota; UI resets', async () => {
  let fail
  const response = new Promise((resolve, reject) => { fail = reject })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 1 },
      limits: { fetches_per_day: 5 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={86400}
    />
  )

  fireEvent.click(getByLabelText('OFF'))

  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 86400)
  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('2 of 5 updates/day') // from state

  await act(async () => { fail(new ErrorResponse('AutofetchQuotaExceeded')) })

  getByLabelText('OFF') // was reset
  getByText('1 of 5 updates/day') // from state
})

test('User edits twice before server responds', async () => {
  let done
  const response = new Promise((resolve, reject) => { done = resolve })

  const store = mockStore({
    loggedInUser: {
      usage: { fetchesPerDay: 1 },
      limits: { fetches_per_day: 50 },
      subscribedStripeProductIds: []
    }
  })

  const api = { trySetStepAutofetch: jest.fn(() => response) }

  const { getByLabelText, getByText, queryByText, rerender } = renderWithStoreAndApi(
    store,
    api,
    <UpdateFrequencySelectModal
      {...TypicalInitialProps}
      isAutofetch={false}
      fetchInterval={86400}
    />
  )

  fireEvent.click(getByLabelText('OFF'))
  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 86400)
  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('2 of 50 updates/day') // from state

  fireEvent.change(getByLabelText('Check for updates every'), { target: { value: 3600 } })
  expect(api.trySetStepAutofetch).toHaveBeenCalledWith('step-2', true, 3600)
  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  done({}) // both API calls respond. Redux store hasn't been updated yet; two updates remain
  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  // One update: the "loggedInUser" changes
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 2 } } } })
  store.dispatch({ type: 'APPLY_DELTA', payload: { updateUser: { usage: { fetchesPerDay: 25 } } } })
  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  // The other update: the workflow changes
  rerender(<UpdateFrequencySelectModal {...TypicalInitialProps} isAutofetch={true} fetchInterval={86400} />)
  rerender(<UpdateFrequencySelectModal {...TypicalInitialProps} isAutofetch={true} fetchInterval={3600} />)
  getByLabelText('ON') // exists
  getByText('Saving…')
  getByText('25 of 50 updates/day') // from state

  await waitForElementToBeRemoved(() => queryByText('Saving…'))
  getByLabelText('ON') // exists
  getByText('25 of 50 updates/day') // from state
})
