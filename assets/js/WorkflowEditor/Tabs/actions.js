import * as util from './util'
import { generateSlug } from '../../utils'
import addLocalMutation from '../../reducers/addLocalMutation'
import addPendingMutation from '../../reducers/addPendingMutation'
import removePendingMutation from '../../reducers/removePendingMutation'
import selectIsReadOnly from '../../selectors/selectIsReadOnly'
import selectOptimisticState from '../../selectors/selectOptimisticState'

import {
  TAB_CREATE,
  TAB_DESTROY,
  TAB_SELECT,
  TAB_SET_ORDER,
  TAB_SET_NAME,
  createCreateMutation,
  createDestroyMutation,
  createSelectMutation,
  createSetNameMutation,
  createSetOrderMutation
} from './mutations'

const TAB_DUPLICATE = 'TAB_DUPLICATE'
const TAB_REMOVE_PENDING_MUTATION = 'TAB_REMOVE_PENDING_MUTATION'

function reduceRemovePendingMutation (state, action) {
  return removePendingMutation(state, action.payload.id)
}

async function removePendingMutationOnError (apiPromise, dispatch, mutationId) {
  try {
    await apiPromise
  } catch (err) {
    dispatch({
      type: TAB_REMOVE_PENDING_MUTATION,
      payload: { id: mutationId, error: err }
    })
    throw err
  }
}

export function setName (slug, name) {
  const mutationId = generateSlug('mutation-')

  return (dispatch, getState, api) => {
    return dispatch({
      type: TAB_SET_NAME,
      payload: {
        promise: removePendingMutationOnError(
          api.setTabName(slug, name, mutationId),
          dispatch,
          mutationId
        ),
        data: { slug, name, mutationId }
      }
    })
  }
}

export function setOrder (tabSlugs) {
  const mutationId = generateSlug('mutation-')

  return (dispatch, getState, api) => {
    return dispatch({
      type: TAB_SET_ORDER,
      payload: {
        promise: removePendingMutationOnError(
          api.setTabOrder(tabSlugs, mutationId),
          dispatch,
          mutationId
        ),
        data: { tabSlugs }
      }
    })
  }
}

export function destroy (slug) {
  return (dispatch, getState, api) => {
    if (selectOptimisticState(getState()).workflow.tab_slugs.length <= 1) {
      return
    }

    const mutationId = generateSlug('mutation-')

    return dispatch({
      type: TAB_DESTROY,
      payload: {
        promise: removePendingMutationOnError(
          api.deleteTab(slug, mutationId),
          dispatch,
          mutationId
        ),
        data: { slug, mutationId }
      }
    })
  }
}

export function select (slug) {
  return (dispatch, getState, api) => {
    const state = selectOptimisticState(getState())

    if (!state.workflow.tab_slugs.includes(slug)) {
      // This happens if the user clicks a "delete" button on the step:
      // 2. Browser dispatches "delete", which removes the tab
      // 1. Browser dispatches "click", which tries to select it
      // https://www.pivotaltracker.com/story/show/162803752
      return
    }

    // Only send API request if we're read-write
    const promise = selectIsReadOnly(state)
      ? Promise.resolve(null)
      : api.setSelectedTab(slug)
    return dispatch({
      type: TAB_SELECT,
      payload: {
        promise,
        data: { slug }
      }
    })
  }
}

export function create (tabPrefix) {
  return (dispatch, getState, api) => {
    const state = selectOptimisticState(getState())
    const mutationId = generateSlug('mutation-')
    const { workflow, tabs } = selectOptimisticState(state)

    const tabNames = []
    for (const k in tabs) {
      tabNames.push(tabs[k].name)
    }

    const slug = generateSlug('tab-')
    const name = util.generateTabName(
      new RegExp(util.escapeRegExp(tabPrefix) + ' (\\d+)'),
      tabPrefix + ' %d',
      tabNames
    )

    return dispatch({
      type: TAB_CREATE,
      payload: {
        promise: removePendingMutationOnError(
          api.createTab(slug, name, mutationId).then(() => ({ slug, name })),
          dispatch,
          mutationId
        ),
        data: {
          slug,
          name,
          mutationId,
          position: workflow.tab_slugs.length
        } // append
      }
    })
  }
}

export function duplicate (oldSlug) {
  return (dispatch, getState, api) => {
    const { workflow, tabs } = selectOptimisticState(getState())
    const mutationId = generateSlug('mutation-')

    const tabNames = []
    Object.values(tabs).forEach(tab => { tabNames.push(tab.name) })

    const oldTab = tabs[oldSlug]
    const oldNameBase = oldTab.name.replace(/ \((\d+)\)$/, '')
    const slug = generateSlug('tab-')
    const nameRegex = new RegExp(
      util.escapeRegExp(oldNameBase) + ' \\((\\d+)\\)'
    )
    const namePattern = oldNameBase + ' (%d)'
    const name = util.generateTabName(nameRegex, namePattern, tabNames)

    return dispatch({
      type: TAB_DUPLICATE,
      payload: {
        promise: removePendingMutationOnError(
          api.duplicateTab(oldSlug, slug, name, mutationId).then(() => ({ slug, name })),
          dispatch,
          mutationId
        ),
        data: {
          slug,
          name,
          mutationId,
          // Insert after oldTab.
          //
          // This is what the server will do; we must mimic it or the user will
          // see the tab change position once the server responds with its
          // authoritative order.
          position: workflow.tab_slugs.indexOf(oldSlug) + 1
        }
      }
    })
  }
}

function reduceCreatePending (state, action) {
  return addPendingMutation(state, createCreateMutation(action.payload))
}

function reduceDuplicatePending (state, action) {
  // BUG: this doesn't add the modules to the new tab.
  //
  // One way to solve this would be to add all the steps in a single action
  // on the client side (instead of letting the server side compute what to
  // duplicate and how).
  return reduceCreatePending(state, action)
}

function reduceDestroyPending (state, action) {
  return addPendingMutation(state, createDestroyMutation(action.payload))
}

function reduceSetNamePending (state, action) {
  return addPendingMutation(state, createSetNameMutation(action.payload))
}

function reduceSelectPending (state, action) {
  return addLocalMutation(state, createSelectMutation(action.payload))
}

function reduceSetOrderPending (state, action) {
  return addPendingMutation(state, createSetOrderMutation(action.payload))
}

export const reducerFunctions = {
  [TAB_CREATE + '_PENDING']: reduceCreatePending,
  [TAB_DUPLICATE + '_PENDING']: reduceDuplicatePending,
  [TAB_DESTROY + '_PENDING']: reduceDestroyPending,
  [TAB_SET_NAME + '_PENDING']: reduceSetNamePending,
  [TAB_SELECT + '_PENDING']: reduceSelectPending,
  [TAB_SET_ORDER + '_PENDING']: reduceSetOrderPending,
  [TAB_REMOVE_PENDING_MUTATION]: reduceRemovePendingMutation
}
