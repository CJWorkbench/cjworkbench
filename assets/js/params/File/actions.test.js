/* globals describe, expect, it, jest, File */
import { mockStore, createConditionVariable } from '../../test-utils'
import * as actions from './actions'

describe('File.actions', () => {
  describe('upload', () => {
    it('should set inProgressUpload, update progress, and set done', async () => {
      let setUploadComplete
      const api = {
        uploadFile: jest.fn(
          () =>
            new Promise(resolve => {
              setUploadComplete = resolve
            })
        )
      }
      const store = mockStore(
        {
          steps: {
            1: { id: 1, foo: 'bar', slug: 'step-1' },
            2: { id: 2, foo: 'baz', slug: 'step-2' }
          }
        },
        api
      )
      const file = new File(['A\nab'], 't.csv')

      // upload
      const done = store.dispatch(actions.upload('step-2', file))
      expect(api.uploadFile).toHaveBeenCalled()
      expect(api.uploadFile.mock.calls[0].slice(0, 2)).toEqual(['step-2', file])
      const setProgress = api.uploadFile.mock.calls[0][2]
      expect(store.getState().steps['2']).toEqual({
        id: 2,
        slug: 'step-2',
        foo: 'baz',
        inProgressUpload: {
          name: 't.csv',
          size: 4,
          nBytesUploaded: null
        }
      })

      // setProgress (callback invoked by the API)
      setProgress(3)
      expect(
        store.getState().steps['2'].inProgressUpload.nBytesUploaded
      ).toEqual(3)

      // completion
      setUploadComplete(undefined)
      await done
      expect(store.getState().steps['2']).toEqual({
        id: 2,
        slug: 'step-2',
        foo: 'baz',
        inProgressUpload: null
      })
    })
  })

  describe('cancel', () => {
    it('should no-op when there is no upload', async () => {
      const api = { cancel: jest.fn() }
      const store = mockStore({ steps: { 1: { id: 1, slug: 'step-1' } } }, api)
      await store.dispatch(actions.cancel('step-1'))
      expect(api.cancel).not.toHaveBeenCalled()
      expect(store.getState().steps['1'].inProgressUpload).toBe(null)
    })

    it('should cancel an upload through the API', async () => {
      const [setCancelled, cancelled] = createConditionVariable()
      const api = {
        cancelFileUpload: jest.fn(() => cancelled)
      }
      const store = mockStore(
        {
          steps: {
            1: { id: 1, slug: 'step-1', foo: 'bar' },
            2: {
              id: 2,
              slug: 'step-2',
              foo: 'baz',
              inProgressUpload: { name: 't.csv', size: 4, nBytesUploaded: 3 }
            }
          }
        },
        api
      )

      // Begin the cancellation (sending a message to the server)
      const done = store.dispatch(actions.cancel('step-2'))
      expect(api.cancelFileUpload).toHaveBeenCalledWith('step-2')
      expect(store.getState().steps['2']).toEqual({
        id: 2,
        slug: 'step-2',
        foo: 'baz',
        inProgressUpload: {
          name: 't.csv',
          size: 4,
          nBytesUploaded: null // so we'll show a spinner
        }
      })

      // Server says cancellation succeeded
      setCancelled()
      await done
      expect(store.getState().steps['2']).toEqual({
        id: 2,
        slug: 'step-2',
        foo: 'baz',
        inProgressUpload: null
      })
    })
  })
})
