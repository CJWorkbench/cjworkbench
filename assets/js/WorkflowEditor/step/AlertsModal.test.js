/* globals expect, jest, test */
import { fireEvent, render } from '@testing-library/react'
import { Provider } from 'react-redux'
import { I18nWrapper } from '../../i18n/test-utils'
import { mockStore } from '../../test-utils'
import AlertsModal from './AlertsModal'

function renderWithStore (store, children) {
  function Wrapper (props) {
    return (
      <I18nWrapper>
        <Provider store={store}>
          {props.children}
        </Provider>
      </I18nWrapper>
    )
  }
  return render(children, { wrapper: Wrapper })
}

test('user enables alerts', async () => {
  const api = { setStepNotifications: jest.fn(() => Promise.resolve(null)) }
  const store = mockStore({
    steps: {
      1: { notifications: false }
    }
  }, api)

  const { getByLabelText, rerender } = renderWithStore(
    store, <AlertsModal stepId={1} checked={false} onClose={jest.fn()} />
  )

  expect(getByLabelText(/Alerts are OFF/).checked).toBe(false)
  fireEvent.click(getByLabelText(/Alerts are OFF/))
  expect(api.setStepNotifications).toHaveBeenCalledWith(1, true)
  rerender(<AlertsModal stepId={1} checked onClose={jest.fn()} />)
  expect(getByLabelText(/Alerts are ON/).checked).toBe(true)
})

test('user disables alerts', async () => {
  const api = { setStepNotifications: jest.fn(() => Promise.resolve(null)) }
  const store = mockStore({
    steps: {
      1: { notifications: true }
    }
  }, api)

  const { getByLabelText, rerender } = renderWithStore(
    store, <AlertsModal stepId={1} checked onClose={jest.fn()} />
  )

  expect(getByLabelText(/Alerts are ON/).checked).toBe(true)
  fireEvent.click(getByLabelText(/Alerts are ON/))
  expect(api.setStepNotifications).toHaveBeenCalledWith(1, false)
  rerender(<AlertsModal stepId={1} checked={false} onClose={jest.fn()} />)
  expect(getByLabelText(/Alerts are OFF/).checked).toBe(false)
})
