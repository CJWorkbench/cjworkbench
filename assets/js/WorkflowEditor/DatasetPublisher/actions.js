import { generateSlug } from '../../utils'

const PUBLISH_DATASET_BEGIN = 'PUBLISH_DATASET_BEGIN'
const PUBLISH_DATASET_RESULT = 'PUBLISH_DATASET_RESULT'

export function beginPublishDataset () {
  const requestId = generateSlug('publish-dataset-')
  return (dispatch, getState, api) => {
    return dispatch({
      type: PUBLISH_DATASET_BEGIN,
      payload: {
        promise: api.beginPublishDataset({ requestId }),
        data: { requestId }
      }
    })
  }
}

function reducePublishBeginPending (state, action) {
  const { requestId } = action.payload
  return { ...state, lastPublishDatasetRequest: { requestId } }
}

function reducePublishResult (state, action) {
  const { error, requestId, datapackage } = action.payload
  if (state.lastPublishDatasetRequest && state.lastPublishDatasetRequest.requestId === requestId) {
    return {
      ...state,
      lastPublishDatasetRequest: action.payload,
      dataset: error ? state.dataset : datapackage
    }
  } else {
    return state
  }
}

export const reducerFunctions = {
  [PUBLISH_DATASET_BEGIN + '_PENDING']: reducePublishBeginPending,
  [PUBLISH_DATASET_RESULT]: reducePublishResult
}
