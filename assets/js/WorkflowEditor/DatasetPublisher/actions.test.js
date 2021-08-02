/* globals expect, jest, test */
import { mockStore } from '../../test-utils'
import { generateSlug } from '../../utils'
import { beginPublishDataset } from './actions'

jest.mock('../../utils')

test('beginPublishDataset() sends API request', async () => {
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const api = { beginPublishDataset: jest.fn(() => Promise.resolve(null)) }
  const store = mockStore({ workflow: { id: 123 } }, api)
  await store.dispatch(beginPublishDataset())
  expect(api.beginPublishDataset).toHaveBeenCalledWith({ requestId: 'publish-dataset-X' })
  expect(store.getState().lastPublishDatasetRequest).toEqual({ requestId: 'publish-dataset-X' })
})

test.todo('beginPublishDataset() handles delta-id-mismatch error')

test('PUBLISH_DATASET_RESULT with success', async () => {
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const store = mockStore({
    workflow: { id: 123 },
    lastPublishDatasetRequest: { requestId: 'publish-dataset-X' }
  })
  await store.dispatch({
    type: 'PUBLISH_DATASET_RESULT',
    payload: {
      requestId: 'publish-dataset-X',
      error: null,
      datapackage: { path: 'https://api-platform/foo/bar' }
    }
  })
  expect(store.getState().lastPublishDatasetRequest).toEqual({
    requestId: 'publish-dataset-X',
    error: null,
    datapackage: { path: 'https://api-platform/foo/bar' }
  })
  expect(store.getState().dataset).toEqual({ path: 'https://api-platform/foo/bar' })
})

test('PUBLISH_DATASET_RESULT with error', async () => {
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const store = mockStore({
    workflow: { id: 123 },
    lastPublishDatasetRequest: { requestId: 'publish-dataset-X' }
  })
  await store.dispatch({
    type: 'PUBLISH_DATASET_RESULT',
    payload: {
      requestId: 'publish-dataset-X',
      error: 'delta-id-mismatch',
      datapackage: null
    }
  })
  expect(store.getState().lastPublishDatasetRequest).toEqual({
    requestId: 'publish-dataset-X',
    error: 'delta-id-mismatch',
    datapackage: null
  })
})

test('PUBLISH_DATASET_RESULT with not-the-most-recent requestId', async () => {
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const store = mockStore({
    workflow: { id: 123 },
    lastPublishDatasetRequest: { requestId: 'publish-dataset-X' }
  })
  await store.dispatch({
    type: 'PUBLISH_DATASET_RESULT',
    payload: {
      requestId: 'publish-dataset-Y',
      error: 'delta-id-mismatch',
      datapackage: null
    }
  })
  expect(store.getState().lastPublishDatasetRequest).toEqual({
    requestId: 'publish-dataset-X'
  })
})
