import { mockStore, createConditionVariable } from '../../test-utils'
import * as actions from './actions'

describe('File.actions', () => {
  describe('upload', () => {
    it('should set inProgressUpload, update progress, and set done', async () => {
      let setUploadComplete
      const api = {
        uploadFile: jest.fn(() => new Promise(resolve => { setUploadComplete = resolve }))
      }
      const store = mockStore({
        wfModules: {
          '1': { foo: 'bar' },
          '2': { foo: 'baz' }
        }
      }, api)
      const file = new File(['A\nab'], 't.csv')

      // upload
      const done = store.dispatch(actions.upload(2, file))
      expect(api.uploadFile).toHaveBeenCalled()
      expect(api.uploadFile.mock.calls[0].slice(0, 2)).toEqual([2, file])
      const setProgress = api.uploadFile.mock.calls[0][2]
      expect(store.getState().wfModules['2']).toEqual({
        foo: 'baz',
        inProgressUpload: {
          name: 't.csv',
          size: 4,
          nBytesUploaded: null
        }
      })

      // setProgress (callback invoked by the API)
      setProgress(3)
      expect(store.getState().wfModules['2'].inProgressUpload.nBytesUploaded).toEqual(3)

      // completion
      setUploadComplete({ uuid: '1234' })
      const result = await done
      expect(store.getState().wfModules['2']).toEqual({
        foo: 'baz',
        inProgressUpload: null
      })

      // should return UUID
      expect(result.value.uuid).toEqual('1234')
    })
  })

  describe('cancel', () => {
    it('should no-op when there is no upload', async () => {
      const api = { cancel: jest.fn() }
      const store = mockStore({ wfModules: { '1': {} } }, api)
      await store.dispatch(actions.cancel(1))
      expect(api.cancel).not.toHaveBeenCalled()
      expect(store.getState().wfModules['1'].inProgressUpload).toBe(null)
    })

    it('should cancel an upload through the API', async () => {
      const [ setCancelled, cancelled ] = createConditionVariable()
      const api = {
        cancelFileUpload: jest.fn(() => cancelled)
      }
      const store = mockStore({
        wfModules: {
          '1': { foo: 'bar' },
          '2': { foo: 'baz', inProgressUpload: { name: 't.csv', size: 4, nBytesUploaded: 3 } }
        }
      }, api)

      // Begin the cancellation (sending a message to the server)
      const done = store.dispatch(actions.cancel(2))
      expect(api.cancelFileUpload).toHaveBeenCalledWith(2)
      expect(store.getState().wfModules['2']).toEqual({
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
      expect(store.getState().wfModules['2']).toEqual({ foo: 'baz', inProgressUpload: null })
    })
  })
})
