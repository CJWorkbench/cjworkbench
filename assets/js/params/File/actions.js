const FILE_UPLOAD = 'FILE_UPLOAD'
const FILE_UPLOAD_CANCEL = 'FILE_UPLOAD_CANCEL'
const FILE_UPLOAD_PROGRESS = 'FILE_UPLOAD_PROGRESS'
const API_TOKEN_NO_OP = 'API_TOKEN_NO_OP'

/**
 * Begin uploading the File in question.
 *
 * File docs: https://developer.mozilla.org/en-US/docs/Web/API/File
 */
export function upload (stepSlug, file) {
  return (dispatch, getState, api) => {
    const onProgress = (nBytesUploaded) => dispatch(setProgress(stepSlug, nBytesUploaded))
    return dispatch({
      type: FILE_UPLOAD,
      payload: {
        // `api.uploadFile` will never error. At worst, it will retry indefinitely.
        promise: api.uploadFile(stepSlug, file, onProgress).then(result => ({ stepSlug })),
        data: { stepSlug, name: file.name, size: file.size }
      }
    })
  }
}

/**
 * Modify step.inProgressUpload in `state`.
 */
function updateStepInProgressFileUpload (state, stepSlug, updateOrNull) {
  const step = findStep(state, stepSlug)
  return step === null ? state : {
    ...state,
    steps: {
      ...state.steps,
      [String(step.id)]: {
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
  const { stepSlug, name, size } = action.payload
  // `nBytesUploaded === null` will render as an "indeterminate" progressbar.
  return updateStepInProgressFileUpload(state, stepSlug, { name, size, nBytesUploaded: null })
}

function reduceUploadFulfilled (state, action) {
  const { stepSlug } = action.payload
  return updateStepInProgressFileUpload(state, stepSlug, null)
}

function findStep (state, stepSlug) {
  // https://www.pivotaltracker.com/story/show/167600824
  return Object.values(state.steps).find(({ slug }) => slug === stepSlug) || null
}

/**
 * Cancel any upload on `step`.
 */
export function cancel (stepSlug) {
  return (dispatch, getState, api) => {
    const step = findStep(getState(), stepSlug)
    const hasUpload = Boolean(step && step.inProgressUpload)
    return dispatch({
      type: FILE_UPLOAD_CANCEL,
      payload: {
        promise: (hasUpload ? api.cancelFileUpload(stepSlug) : Promise.resolve(null)).then(() => ({ stepSlug })),
        data: { stepSlug }
      }
    })
  }
}

function reduceCancelPending (state, action) {
  const { stepSlug } = action.payload
  // `nBytesUploaded === null` will render as an "indeterminate" progressbar.
  return updateStepInProgressFileUpload(state, stepSlug, { nBytesUploaded: null })
}

function reduceCancelFulfilled (state, action) {
  const { stepSlug } = action.payload
  return updateStepInProgressFileUpload(state, stepSlug, null)
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
export function getApiToken (stepSlug) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: API_TOKEN_NO_OP,
      payload: {
        promise: api.getStepFileUploadApiToken(stepSlug)
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
