const FILE_UPLOAD = 'FILE_UPLOAD'
const FILE_UPLOAD_CANCEL = 'FILE_UPLOAD_CANCEL'
const FILE_UPLOAD_PROGRESS = 'FILE_UPLOAD_PROGRESS'
const API_TOKEN_NO_OP = 'API_TOKEN_NO_OP'

/**
 * Begin uploading the File in question.
 *
 * File docs: https://developer.mozilla.org/en-US/docs/Web/API/File
 */
export function upload (stepId, file) {
  return (dispatch, getState, api) => {
    const onProgress = (nBytesUploaded) => dispatch(setProgress(stepId, nBytesUploaded))
    return dispatch({
      type: FILE_UPLOAD,
      payload: {
        // `api.uploadFile` will never error. At worst, it will retry indefinitely.
        promise: api.uploadFile(stepId, file, onProgress)
          .then(result => ({
            stepId,
            uuid: result === null ? null : result.uuid
          })),
        data: { stepId, name: file.name, size: file.size }
      }
    })
  }
}

/**
 * Modify step.inProgressUpload in `state`.
 */
function updateStepInProgressFileUpload (state, stepId, updateOrNull) {
  const { steps } = state
  const step = steps[String(stepId)]
  return {
    ...state,
    steps: {
      ...steps,
      [stepId]: {
        ...step,
        inProgressUpload: updateOrNull === null ? null : {
          ...(step.inProgressUpload || {}),
          ...updateOrNull
        }
      }
    }
  }
}

function reduceUploadPending (state, action) {
  const { stepId, name, size } = action.payload
  // `nBytesUploaded === null` will render as an "indeterminate" progressbar.
  return updateStepInProgressFileUpload(state, stepId, { name, size, nBytesUploaded: null })
}

function reduceUploadFulfilled (state, action) {
  const { stepId } = action.payload
  return updateStepInProgressFileUpload(state, stepId, null)
}

/**
 * Cancel any upload on `step`.
 */
export function cancel (stepId) {
  return (dispatch, getState, api) => {
    const hasUpload = !!getState().steps[String(stepId)].inProgressUpload
    return dispatch({
      type: FILE_UPLOAD_CANCEL,
      payload: {
        promise: (hasUpload ? api.cancelFileUpload(stepId) : Promise.resolve(null)).then(() => ({ stepId })),
        data: { stepId }
      }
    })
  }
}

function reduceCancelPending (state, action) {
  const { stepId } = action.payload
  // `nBytesUploaded === null` will render as an "indeterminate" progressbar.
  return updateStepInProgressFileUpload(state, stepId, { nBytesUploaded: null })
}

function reduceCancelFulfilled (state, action) {
  const { stepId } = action.payload
  return updateStepInProgressFileUpload(state, stepId, null)
}

/**
 * Mark a File upload as progressing.
 */
export function setProgress (stepId, nBytesUploaded) {
  return {
    type: FILE_UPLOAD_PROGRESS,
    payload: { stepId, nBytesUploaded }
  }
}

function reduceSetProgress (state, action) {
  const { stepId, nBytesUploaded } = action.payload
  return updateStepInProgressFileUpload(state, stepId, { nBytesUploaded })
}

/**
 * Call API method to get API token.
 *
 * API token is not stored in Redux state because Redux state is the same for
 * all users, even users without write permission.
 *
 * Return a url-safe string.
 */
export function getApiToken (stepId) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: API_TOKEN_NO_OP,
      payload: {
        promise: api.getStepFileUploadApiToken(stepId)
      }
    })
  }
}

/**
 * Call API method to set a new API token.
 *
 * API token is not stored in Redux state because Redux state is the same for
 * all users, even users without write permission.
 *
 * Return a url-safe string.
 */
export function resetApiToken (stepId) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: API_TOKEN_NO_OP,
      payload: {
        promise: api.resetStepFileUploadApiToken(stepId)
      }
    })
  }
}

/**
 * Call API method to disallow API file uploads.
 *
 * API token is not stored in Redux state because Redux state is the same for
 * all users, even users without write permission.
 */
export function clearApiToken (stepId) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: API_TOKEN_NO_OP,
      payload: {
        promise: api.clearStepFileUploadApiToken(stepId)
      }
    })
  }
}

export const reducerFunctions = {
  [FILE_UPLOAD + '_PENDING']: reduceUploadPending,
  [FILE_UPLOAD + '_FULFILLED']: reduceUploadFulfilled,
  [FILE_UPLOAD_CANCEL + '_PENDING']: reduceCancelPending,
  [FILE_UPLOAD_CANCEL + '_FULFILLED']: reduceCancelFulfilled,
  [FILE_UPLOAD_PROGRESS]: reduceSetProgress
  // No reducers for API_TOKEN_NO_OP -- state doesn't change.
}
