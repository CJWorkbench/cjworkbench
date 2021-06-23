/* globals afterEach, beforeEach, expect, jest, test */
import { I18nWrapper } from '../i18n/test-utils'
import { fireEvent, render } from '@testing-library/react'
import { Provider } from 'react-redux'
import { mockStore } from '../test-utils'
import DataVersionModal, { formatDateUTCForTesting } from './DataVersionModal'

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

beforeEach(() => formatDateUTCForTesting(true))
afterEach(() => formatDateUTCForTesting(false))

test('show versions', () => {
  const store = mockStore({
    steps: {
      1: {
        versions: {
          versions: [
            ['1970-01-03T17:09:27.890000Z', 'extra', 'ignored', 'stuff'],
            ['1970-01-02T10:17:36.789000Z', 'DELETEME', 'server', 'should', 'send', 'real', 'ids']
          ],
          selected: '1970-01-02T10:17:36.789000Z'
        }
      }
    }
  })
  const { getByLabelText } = renderWithStore(
    store,
    <DataVersionModal stepId={1} onClose={jest.fn()} onChangeFetchVersionId={jest.fn()} />
  )
  expect(getByLabelText('Jan 3, 1970, 5:09 PM UTC').checked).toBe(false)
  expect(getByLabelText('Jan 2, 1970, 10:17 AM UTC').checked).toBe(true)
})

test('select a version', () => {
  const api = { setStepVersion: jest.fn(() => Promise.resolve(null)) }
  const store = mockStore({
    steps: {
      1: {
        versions: {
          versions: [
            ['1970-01-03T17:09:27.890000Z', 'extra', 'ignored', 'stuff'],
            ['1970-01-02T10:17:36.789000Z', 'DELETEME', 'server', 'should', 'send', 'real', 'ids']
          ],
          selected: '1970-01-02T10:17:36.789000Z'
        }
      }
    }
  }, api)
  const { getByLabelText, getByText } = renderWithStore(
    store,
    <DataVersionModal stepId={1} onClose={jest.fn()} onChangeFetchVersionId={jest.fn()} />
  )
  fireEvent.click(getByLabelText('Jan 3, 1970, 5:09 PM UTC'))
  fireEvent.click(getByText('Load'))
  expect(api.setStepVersion).toHaveBeenCalledWith(1, '1970-01-03T17:09:27.890000Z')
  expect(getByLabelText('Jan 3, 1970, 5:09 PM UTC').checked).toBe(true)
})

test('cancel with the close button', () => {
  const api = { setStepVersion: jest.fn() }
  const store = mockStore({
    steps: {
      1: {
        versions: {
          versions: [
            ['1970-01-03T17:09:27.890000Z', 'extra', 'ignored', 'stuff'],
            ['1970-01-02T10:17:36.789000Z', 'DELETEME', 'server', 'should', 'send', 'real', 'ids']
          ],
          selected: '1970-01-02T10:17:36.789000Z'
        }
      }
    }
  }, api)
  const onClose = jest.fn()
  const { getByLabelText, getByRole } = renderWithStore(
    store,
    <DataVersionModal stepId={1} onClose={onClose} onChangeFetchVersionId={jest.fn()} />
  )
  fireEvent.click(getByLabelText('Jan 3, 1970, 5:09 PM UTC'))
  fireEvent.click(getByRole('button', { name: /Close/ }))
  expect(api.setStepVersion).not.toHaveBeenCalled()
  expect(onClose).toHaveBeenCalled()
})
