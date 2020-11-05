import { generateSlug } from '../../utils'
import addOptimisticUpdate from '../../reducers/addOptimisticUpdate'
import removeOptimisticUpdate from '../../reducers/removeOptimisticUpdate'
import selectOptimisticState from '../../selectors/selectOptimisticState'
import selectReport from '../../selectors/selectReport'

const REPORT_ADD_BLOCK = 'REPORT_ADD_BLOCK'
const REPORT_DELETE_BLOCK = 'REPORT_DELETE_BLOCK'
const REPORT_REORDER_BLOCKS = 'REPORT_REORDER_BLOCKS'
const REPORT_SET_BLOCK_MARKDOWN = 'REPORT_SET_BLOCK_MARKDOWN'
const REPORT_REMOVE_OPTIMISTIC_UPDATE = 'REPORT_REMOVE_OPTIMISTIC_UPDATE'

function splice (array, position, value) {
  return [...array.slice(0, position), value, ...array.slice(position)]
}

function reduceRemoveOptimisticUpdate (state, action) {
  return removeOptimisticUpdate(state, action.payload)
}

async function removeOptimisticUpdateOnError (apiPromise, dispatch, optimisticUpdateId) {
  try {
    await apiPromise
  } catch (err) {
    dispatch({
      type: REPORT_REMOVE_OPTIMISTIC_UPDATE,
      payload: { id: optimisticUpdateId, error: err }
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
  const optimisticUpdateId = generateSlug('update-')
  const slug = generateSlug('block-')
  const args = {
    slug,
    position,
    optimisticUpdateId,
    ...block
  }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_ADD_BLOCK,
      payload: {
        data: {
          optimisticUpdateId,
          slug,
          position,
          block
        },
        promise: removeOptimisticUpdateOnError(api.addBlock(args), dispatch, optimisticUpdateId)
      }
    })
  }
}

function buildAddBlockToCustomReportOptimisticUpdate (state, slug, position, block) {
  return {
    updateWorkflow: {
      blockSlugs: splice(state.workflow.blockSlugs, position, slug)
    },
    updateBlocks: {
      [slug]: block
    }
  }
}

function reportBlockToStateBlock (block) {
  switch (block.type) {
    case 'chart': return { type: block.type, stepSlug: block.step.slug }
    case 'table': return { type: block.type, tabSlug: block.tab.slug }
    case 'text': return { type: block.type, markdown: block.markdown }
    default: throw new Error('Unknown block type')
  }
}

function buildAddBlockToAutoReportOptimisticUpdate (state, slug, position, block) {
  const autoBlocks = selectReport(state)
  const autoBlocksBySlug = {}
  autoBlocks.forEach(block => {
    autoBlocksBySlug[block.slug] = reportBlockToStateBlock(block)
  })
  return {
    updateWorkflow: {
      hasCustomReport: true,
      blockSlugs: splice(autoBlocks.map(b => b.slug), position, slug)
    },
    updateBlocks: {
      ...autoBlocksBySlug,
      [slug]: block
    }
  }
}

function reduceAddBlockPending (state, action) {
  const { optimisticUpdateId, slug, position, block } = action.payload
  const optimisticState = selectOptimisticState(state)
  const update = optimisticState.workflow.hasCustomReport
    ? buildAddBlockToCustomReportOptimisticUpdate(optimisticState, slug, position, block)
    : buildAddBlockToAutoReportOptimisticUpdate(optimisticState, slug, position, block)
  return addOptimisticUpdate(state, {
    ...update,
    optimisticId: optimisticUpdateId
  })
}

/**
 * Delete a block with the given slug.
 */
export function deleteBlock (slug) {
  const optimisticUpdateId = generateSlug('update-')
  const args = { slug, optimisticUpdateId }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_DELETE_BLOCK,
      payload: {
        data: args,
        promise: removeOptimisticUpdateOnError(api.deleteBlock(args), dispatch, optimisticUpdateId)
      }
    })
  }
}

function buildDeleteBlockFromCustomReportOptimisticUpdate (state, slug) {
  return {
    updateWorkflow: {
      blockSlugs: state.workflow.blockSlugs.filter(s => s !== slug)
    },
    clearBlockSlugs: [slug]
  }
}

function buildDeleteBlockFromAutoReportOptimisticUpdate (state, slug) {
  const autoBlocks = selectReport(state).filter(b => b.slug !== slug)
  const autoBlocksBySlug = {}
  autoBlocks.forEach(block => {
    autoBlocksBySlug[block.slug] = reportBlockToStateBlock(block)
  })
  return {
    updateWorkflow: {
      hasCustomReport: true,
      blockSlugs: autoBlocks.map(b => b.slug)
    },
    updateBlocks: autoBlocksBySlug
  }
}

function reduceDeleteBlockPending (state, action) {
  const { optimisticUpdateId, slug } = action.payload
  const optimisticState = selectOptimisticState(state)
  const update = optimisticState.workflow.hasCustomReport
    ? buildDeleteBlockFromCustomReportOptimisticUpdate(optimisticState, slug)
    : buildDeleteBlockFromAutoReportOptimisticUpdate(optimisticState, slug)
  return addOptimisticUpdate(state, {
    ...update,
    optimisticId: optimisticUpdateId
  })
}

/**
 * Reorder all blocks to the newly-passed slug order.
 */
export function reorderBlocks (slugs) {
  const optimisticUpdateId = generateSlug('update-')
  const args = { slugs, optimisticUpdateId }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_REORDER_BLOCKS,
      payload: {
        data: args,
        promise: removeOptimisticUpdateOnError(api.reorderBlocks(args), dispatch, optimisticUpdateId)
      }
    })
  }
}

function buildReorderBlocksInCustomReportOptimisticUpdate (state, slugs) {
  return {
    updateWorkflow: {
      blockSlugs: slugs
    }
  }
}

function buildReorderBlocksInAutoReportOptimisticUpdate (state, slugs) {
  const autoBlocks = selectReport(state)
  const autoBlocksBySlug = {}
  autoBlocks.forEach(block => {
    autoBlocksBySlug[block.slug] = reportBlockToStateBlock(block)
  })
  return {
    updateWorkflow: {
      hasCustomReport: true,
      blockSlugs: slugs
    },
    updateBlocks: autoBlocksBySlug
  }
}

function reduceReorderBlocksPending (state, action) {
  const { optimisticUpdateId, slugs } = action.payload
  const optimisticState = selectOptimisticState(state)
  const update = optimisticState.workflow.hasCustomReport
    ? buildReorderBlocksInCustomReportOptimisticUpdate(optimisticState, slugs)
    : buildReorderBlocksInAutoReportOptimisticUpdate(optimisticState, slugs)
  return addOptimisticUpdate(state, {
    ...update,
    optimisticId: optimisticUpdateId
  })
}

/**
 * Set `block.markdown` on a Text block.
 */
export function setBlockMarkdown (slug, markdown) {
  const optimisticUpdateId = generateSlug('update-')
  const args = { slug, markdown, optimisticUpdateId }

  return (dispatch, getState, api) => {
    return dispatch({
      type: REPORT_SET_BLOCK_MARKDOWN,
      payload: {
        data: args,
        promise: removeOptimisticUpdateOnError(api.setBlockMarkdown(args), dispatch, optimisticUpdateId)
      }
    })
  }
}

function reduceSetBlockMarkdownPending (state, action) {
  const { optimisticUpdateId, slug, markdown } = action.payload
  return addOptimisticUpdate(state, {
    optimisticId: optimisticUpdateId,
    updateBlocks: {
      [slug]: { type: 'text', markdown }
    }
  })
}

export const reducerFunctions = {
  [REPORT_ADD_BLOCK + '_PENDING']: reduceAddBlockPending,
  [REPORT_DELETE_BLOCK + '_PENDING']: reduceDeleteBlockPending,
  [REPORT_REORDER_BLOCKS + '_PENDING']: reduceReorderBlocksPending,
  [REPORT_SET_BLOCK_MARKDOWN + '_PENDING']: reduceSetBlockMarkdownPending,
  [REPORT_REMOVE_OPTIMISTIC_UPDATE]: reduceRemoveOptimisticUpdate
}
