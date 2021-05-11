import { generateSlug } from '../../utils'
import addPendingMutation from '../../reducers/addPendingMutation'
import removePendingMutation from '../../reducers/removePendingMutation'
import selectOptimisticState from '../../selectors/selectOptimisticState'

import {
  STEP_LIST_REORDER_STEPS,
  createReorderStepsMutation
} from './mutations'

const STEP_LIST_REMOVE_PENDING_MUTATION = 'STEP_LIST_REMOVE_PENDING_MUTATION'

function reduceRemovePendingMutation (state, action) {
  return removePendingMutation(state, action.payload.id)
}

async function removePendingMutationOnError (apiPromise, dispatch, mutationId) {
  try {
    await apiPromise
  } catch (err) {
    dispatch({
      type: STEP_LIST_REMOVE_PENDING_MUTATION,
      payload: { id: mutationId, error: err }
    })
    throw err
  }
}

/**
 * Move step `slug` to position `position` (0 meaning first).
 */
export function reorderStep (tabSlug, stepSlug, position) {
  const mutationId = generateSlug('mutation-')

  return (dispatch, getState, api) => {
    const { tabs, steps } = selectOptimisticState(getState())
    const oldSlugs = tabs[tabSlug].step_ids.map(id => steps[String(id)].slug)
    const slugs = oldSlugs.filter(slug => slug !== stepSlug) // we'll mutate it
    slugs.splice(position, 0, stepSlug)

    const data = { tabSlug, slugs, mutationId }

    return dispatch({
      type: STEP_LIST_REORDER_STEPS,
      payload: {
        data,
        promise: removePendingMutationOnError(
          api.reorderSteps(data),
          dispatch,
          mutationId
        ).catch(err => {
          // Shouldn't really be a _warning_ if the call fails because of a
          // race. And we shouldn't really catch if the call failed because
          // of a network error. TODO inspect server response to figure out
          // whether to catch or not
          console.warn('reorderSteps failed', err)
        })
      }
    })
  }
}

function reduceReorderStepsPending (state, action) {
  return addPendingMutation(state, createReorderStepsMutation(action.payload))
}

export const reducerFunctions = {
  [STEP_LIST_REORDER_STEPS + '_PENDING']: reduceReorderStepsPending,
  [STEP_LIST_REMOVE_PENDING_MUTATION]: reduceRemovePendingMutation
}
