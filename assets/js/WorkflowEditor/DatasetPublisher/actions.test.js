/* globals expect, jest, test */
import { mockStore } from '../../test-utils'
import { generateSlug } from '../../utils'
import { beginPublishDataset } from './actions'
import { ErrorResponse } from '../../WorkflowWebsocket'

jest.mock('../../utils')

test('beginPublishDataset() sends API request', async () => {
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const api = { beginPublishDataset: jest.fn(() => Promise.resolve(null)) }
  const store = mockStore({ workflow: { id: 123, last_update: '2021-07-27T16:01:02.123456Z' } }, api)
  await store.dispatch(beginPublishDataset())
  expect(api.beginPublishDataset).toHaveBeenCalledWith({ requestId: 'publish-dataset-X', workflowUpdatedAt: '2021-07-27T16:01:02.123456Z' })
  expect(store.getState().lastPublishDatasetRequest).toEqual({ requestId: 'publish-dataset-X' })
})

test('beginPublishDataset() handles updated-at-mismatch error', async () => {
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const api = { beginPublishDataset: jest.fn(() => Promise.reject(new ErrorResponse('updated-at-mismatch'))) }
  const store = mockStore({ workflow: { id: 123, last_update: '2021-07-27T16:01:02.123456Z' } }, api)
  await store.dispatch(beginPublishDataset())
  expect(store.getState().lastPublishDatasetRequest).toEqual({ requestId: 'publish-dataset-X', error: 'updated-at-mismatch', dataset: null })
})

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
