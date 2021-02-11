import { generateSlug } from '../../utils'
import addPendingMutation from '../../reducers/addPendingMutation'
import removePendingMutation from '../../reducers/removePendingMutation'

import {
  REPORT_ADD_BLOCK,
  REPORT_DELETE_BLOCK,
  REPORT_REORDER_BLOCKS,
  REPORT_SET_BLOCK_MARKDOWN,
  createAddBlockMutation,
  createDeleteBlockMutation,
  createReorderBlocksMutation,
  createSetBlockMarkdownMutation
} from './mutations'

const REPORT_REMOVE_PENDING_MUTATION = 'REPORT_REMOVE_PENDING_MUTATION'

function reduceRemovePendingMutation (state, action) {
  return removePendingMutation(state, action.payload.id)
}

async function removePendingMutationOnError (apiPromise, dispatch, mutationId) {
  try {
    await apiPromise
  } catch (err) {
    dispatch({
      type: REPORT_REMOVE_PENDING_MUTATION,
      payload: { id: mutationId, error: err }
    })
    throw err
  }
}

/**
 * Add a block at the given position.
 *
 * `block` may look like:
 *
 * * `{ type: "text", markdown: "abcd" }`
 * * `{ type: "chart", stepSlug: "step-1" }`
 * * `{ type: "table", tabSlug: "tab-1" }`
 */
export function addBlock (position, block) {
  const mutationId = generateSlug('mutation-')
  const slug = generateSlug('block-')
  const args = {
    slug,
    position,
    mutationId,
    ...block
  }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_ADD_BLOCK,
      payload: {
        data: args,
        promise: removePendingMutationOnError(
          api.addBlock(args),
          dispatch,
          mutationId
        )
      }
    })
  }
}

function reduceAddBlockPending (state, action) {
  return addPendingMutation(state, createAddBlockMutation(action.payload))
}

/**
 * Delete a block with the given slug.
 */
export function deleteBlock (slug) {
  const mutationId = generateSlug('mutation-')
  const args = { slug, mutationId }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_DELETE_BLOCK,
      payload: {
        data: args,
        promise: removePendingMutationOnError(
          api.deleteBlock(args),
          dispatch,
          mutationId
        )
      }
    })
  }
}

function reduceDeleteBlockPending (state, action) {
  return addPendingMutation(state, createDeleteBlockMutation(action.payload))
}

/**
 * Reorder all blocks to the newly-passed slug order.
 */
export function reorderBlocks (slugs) {
  const mutationId = generateSlug('mutation-')
  const args = { slugs, mutationId }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_REORDER_BLOCKS,
      payload: {
        data: args,
        promise: removePendingMutationOnError(
          api.reorderBlocks(args),
          dispatch,
          mutationId
        )
      }
    })
  }
}

function reduceReorderBlocksPending (state, action) {
  return addPendingMutation(state, createReorderBlocksMutation(action.payload))
}

/**
 * Set `block.markdown` on a Text block.
 */
export function setBlockMarkdown (slug, markdown) {
  const mutationId = generateSlug('mutation-')
  const args = { slug, markdown, mutationId }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_SET_BLOCK_MARKDOWN,
      payload: {
        data: args,
        promise: removePendingMutationOnError(
          api.setBlockMarkdown(args),
          dispatch,
          mutationId
        )
      }
    })
  }
}

function reduceSetBlockMarkdownPending (state, action) {
  return addPendingMutation(
    state,
    createSetBlockMarkdownMutation(action.payload)
  )
}

export const reducerFunctions = {
  [REPORT_ADD_BLOCK + '_PENDING']: reduceAddBlockPending,
  [REPORT_DELETE_BLOCK + '_PENDING']: reduceDeleteBlockPending,
  [REPORT_REORDER_BLOCKS + '_PENDING']: reduceReorderBlocksPending,
  [REPORT_SET_BLOCK_MARKDOWN + '_PENDING']: reduceSetBlockMarkdownPending,
  [REPORT_REMOVE_PENDING_MUTATION]: reduceRemovePendingMutation
}
