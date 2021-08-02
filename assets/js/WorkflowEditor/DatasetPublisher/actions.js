import { generateSlug } from '../../utils'
import addPendingMutation from '../../reducers/addPendingMutation'
import removePendingMutation from '../../reducers/removePendingMutation'
import { DATASET_SET_TAB_SLUGS, createSetTabSlugsMutation } from './mutations'

const PUBLISH_DATASET_BEGIN = 'PUBLISH_DATASET_BEGIN'
const PUBLISH_DATASET_RESULT = 'PUBLISH_DATASET_RESULT'

const DATASET_REMOVE_PENDING_MUTATION = 'DATASET_REMOVE_PENDING_MUTATION'

function reduceRemovePendingMutation (state, action) {
  return removePendingMutation(state, action.payload.id)
}

async function removePendingMutationOnError (apiPromise, dispatch, mutationId) {
  try {
    await apiPromise
  } catch (err) {
    dispatch({
      type: DATASET_REMOVE_PENDING_MUTATION,
      payload: { id: mutationId, error: err }
    })
    throw err
  }
}

export function setTabSlugs (tabSlugs) {
  const mutationId = generateSlug('mutation-')

  return (dispatch, getState, api) => {
    return dispatch({
      type: DATASET_SET_TAB_SLUGS,
      payload: {
        data: { tabSlugs, mutationId },
        promise: removePendingMutationOnError(
          api.setNextDatasetParams({ mutationId, tabSlugs }),
          dispatch,
          mutationId
        )
      }
    })
  }
}

export function beginPublishDataset () {
  const requestId = generateSlug('publish-dataset-')
  return (dispatch, getState, api) => {
    const workflowUpdatedAt = getState().workflow.last_update
    const promise = api.beginPublishDataset({ requestId, workflowUpdatedAt })
      .catch(error => {
        if (error.serverError === 'updated-at-mismatch') {
          return { error: 'updated-at-mismatch' }
        }
        throw error
      })

    return dispatch({
      type: PUBLISH_DATASET_BEGIN,
      payload: {
        promise,
        data: { requestId }
      }
    })
  }
}

function reduceSetTabSlugsPending (state, action) {
  return addPendingMutation(state, createSetTabSlugsMutation(action.payload))
}

function reducePublishBeginPending (state, action) {
  const { requestId } = action.payload
  return { ...state, lastPublishDatasetRequest: { requestId } }
}

function reducePublishBeginFulfilled (state, action) {
  if (action.payload && action.payload.error) {
    return {
      ...state,
      lastPublishDatasetRequest: {
        ...state.lastPublishDatasetRequest,
        error: action.payload.error,
        dataset: null
      }
    }
  }
  return state
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
  [DATASET_SET_TAB_SLUGS + '_PENDING']: reduceSetTabSlugsPending,
  [DATASET_REMOVE_PENDING_MUTATION]: reduceRemovePendingMutation,
  [PUBLISH_DATASET_BEGIN + '_PENDING']: reducePublishBeginPending,
  [PUBLISH_DATASET_BEGIN + '_FULFILLED']: reducePublishBeginFulfilled,
  [PUBLISH_DATASET_RESULT]: reducePublishResult
}
