/* globals expect, jest, test */
import { act } from 'react-dom/test-utils'
import { fireEvent } from '@testing-library/react'
import { renderWithI18n } from '../i18n/test-utils'
import { Future } from '../test-utils'
import PublicAccess from './PublicAccess'

const DefaultProps = {
  workflowId: 123,
  isReadOnly: false,
  isPublic: false,
  secretId: '',
  canCreateSecretLink: true,
  setWorkflowPublicAccess: jest.fn(),
  logShare: jest.fn()
}

test('private => public', async () => {
  const serverResponse = new Future()
  const setWorkflowPublicAccess = jest.fn(() => serverResponse.promise)
  const { container, getByText, getByLabelText, getByDisplayValue, rerender } = renderWithI18n(
    <PublicAccess {...DefaultProps} isPublic={false} secretId='' setWorkflowPublicAccess={setWorkflowPublicAccess} />
  )

  fireEvent.click(getByText('Public'))
  expect(getByLabelText(/Public/).checked).toBe(true)
  expect(container.querySelector('fieldset').disabled).toBe(true) // because we're submitting

  serverResponse.resolve(null)
  rerender(
    <PublicAccess {...DefaultProps} isPublic secretId='' setWorkflowPublicAccess={setWorkflowPublicAccess} />
  )
  expect(getByLabelText(/Public/).checked).toBe(true)
  await act(async () => await null) // respond to serverResponse.resolve
  expect(container.querySelector('fieldset').disabled).toBe(false)
  getByDisplayValue('http://localhost/workflows/123')
  expect(container.querySelector('a.facebook-share').href).toEqual('https://www.facebook.com/sharer.php?u=http%3A%2F%2Flocalhost%2Fworkflows%2F123')
})

test('public => secret', async () => {
  const serverResponse = new Future()
  const setWorkflowPublicAccess = jest.fn(() => serverResponse.promise)
  const { container, getByText, getByLabelText, getByDisplayValue, rerender } = renderWithI18n(
    <PublicAccess {...DefaultProps} isPublic secretId='' setWorkflowPublicAccess={setWorkflowPublicAccess} />
  )

  fireEvent.click(getByText('Secret link'))
  expect(getByLabelText(/Secret/).checked).toBe(true)
  expect(container.querySelector('fieldset').disabled).toBe(true) // because we're submitting

  serverResponse.resolve(null)
  rerender(
    <PublicAccess {...DefaultProps} isPublic={false} secretId='wsecret' setWorkflowPublicAccess={setWorkflowPublicAccess} />
  )
  expect(getByLabelText(/Secret link/).checked).toBe(true)
  await act(async () => await null) // respond to serverResponse.resolve

  expect(container.querySelector('fieldset').disabled).toBe(false)
  getByDisplayValue('http://localhost/workflows/wsecret')
  expect(container.querySelector('a.facebook-share')).toBe(null)
})

test('secret => private', async () => {
  const serverResponse = new Future()
  const setWorkflowPublicAccess = jest.fn(() => serverResponse.promise)
  const { container, getByText, getByLabelText, queryByText, rerender } = renderWithI18n(
    <PublicAccess {...DefaultProps} isPublic={false} secretId='wsecret' setWorkflowPublicAccess={setWorkflowPublicAccess} />
  )

  fireEvent.click(getByText('Private'))
  expect(getByLabelText(/Secret link/).checked).toBe(true) // Secret link is still selected
  expect(container.querySelector('fieldset').disabled).toBe(false) // a "delete" button needs clicking

  // Now click "Delete" to actually send the server request
  fireEvent.click(getByText('Delete'))
  expect(container.querySelector('fieldset').disabled).toBe(true)
  serverResponse.resolve(null)
  rerender(
    <PublicAccess {...DefaultProps} isPublic={false} secretId='' setWorkflowPublicAccess={setWorkflowPublicAccess} />
  )

  await act(async () => await null) // respond to serverResponse.resolve
  expect(container.querySelector('fieldset').disabled).toBe(false)
  expect(queryByText('Workflow link')).toBe(null)
})

test('cannot edit when read-only', () => {
  const { getByLabelText } = renderWithI18n(
    <PublicAccess {...DefaultProps} isReadOnly isPublic={false} secretId='' />
  )

  expect(getByLabelText(/Private/).checked).toBe(true)
  // The fieldset isn't disabled, because we don't want to gray out text; but
  // every field is disabled
  expect(getByLabelText(/Private/).disabled).toBe(true)
  expect(getByLabelText(/Secret link/).disabled).toBe(true)
  expect(getByLabelText(/Public/).disabled).toBe(true)
})

test('disable "Secret link" and prompt to upgrade when user has no permission', () => {
  const { getByLabelText, queryByText } = renderWithI18n(
    <PublicAccess {...DefaultProps} canCreateSecretLink={false} />
  )

  expect(getByLabelText(/Secret link/).disabled).toBe(true)
  expect(queryByText('Upgrade').tagName).toEqual('A')
})

test('do not prompt to upgrade when read-only', () => {
  const { getByLabelText, queryByText } = renderWithI18n(
    <PublicAccess {...DefaultProps} isReadOnly canCreateSecretLink={false} />
  )

  expect(getByLabelText(/Secret link/).disabled).toBe(true)
  expect(queryByText('Upgrade')).toBe(null)
})

test('do not prompt to upgrade when we have a secret link already', () => {
  const { getByLabelText, queryByText } = renderWithI18n(
    <PublicAccess {...DefaultProps} isPublic={false} secretId='wsecret' canCreateSecretLink={false} />
  )

  expect(getByLabelText(/Secret link/).disabled).toBe(false)
  expect(queryByText('Upgrade')).toBe(null)
})
