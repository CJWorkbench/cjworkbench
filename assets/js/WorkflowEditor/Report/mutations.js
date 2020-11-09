import selectAutoReport from '../../selectors/selectAutoReport'

export const REPORT_ADD_BLOCK = 'REPORT_ADD_BLOCK'
export const REPORT_DELETE_BLOCK = 'REPORT_DELETE_BLOCK'
export const REPORT_REORDER_BLOCKS = 'REPORT_REORDER_BLOCKS'
export const REPORT_SET_BLOCK_MARKDOWN = 'REPORT_SET_BLOCK_MARKDOWN'

function createMutationCreator (type) {
  return ({ mutationId, ...args }) => ({ type, id: mutationId, args })
}

export const createAddBlockMutation = createMutationCreator(REPORT_ADD_BLOCK)
export const createDeleteBlockMutation = createMutationCreator(REPORT_DELETE_BLOCK)
export const createReorderBlocksMutation = createMutationCreator(REPORT_REORDER_BLOCKS)
export const createSetBlockMarkdownMutation = createMutationCreator(REPORT_SET_BLOCK_MARKDOWN)

function insert (array, position, value) {
  return [...array.slice(0, position), value, ...array.slice(position)]
}

function removeByKey (obj, key) {
  const ret = { ...obj }
  delete ret[key]
  return ret
}

function addBlockToCustomReport (state, slug, position, block) {
  if (position > state.workflow.blockSlugs.length) {
    return state
  }

  return {
    ...state,
    workflow: {
      ...state.workflow,
      blockSlugs: insert(state.workflow.blockSlugs, position, slug)
    },
    blocks: {
      ...state.blocks,
      [slug]: block
    }
  }
}

function reportBlockToStateBlock (block) {
  switch (block.type) {
    case 'chart': return { type: block.type, stepSlug: block.step.slug }
    case 'table': return { type: block.type, tabSlug: block.tab.slug }
    case 'text': return { type: block.type, markdown: block.markdown }
    default: throw new Error('Unknown block type ' + block.type)
  }
}

function addBlockToAutoReport (state, slug, position, block) {
  const autoBlocks = selectAutoReport(state)
  if (position > autoBlocks.length) {
    return state
  }

  const autoBlocksBySlug = {}
  autoBlocks.forEach(block => {
    autoBlocksBySlug[block.slug] = reportBlockToStateBlock(block)
  })
  return {
    ...state,
    workflow: {
      ...state.workflow,
      hasCustomReport: true,
      blockSlugs: insert(autoBlocks.map(b => b.slug), position, slug)
    },
    blocks: {
      ...autoBlocksBySlug,
      [slug]: block
    }
  }
}

function deleteBlockFromCustomReport (state, slug) {
  if (!(slug in state.blocks)) {
    return state // no-op
  }

  return {
    ...state,
    workflow: {
      ...state.workflow,
      blockSlugs: state.workflow.blockSlugs.filter(s => s !== slug)
    },
    blocks: removeByKey(state.blocks, slug)
  }
}

function deleteBlockFromAutoReport (state, slug) {
  const autoBlocks = selectAutoReport(state)
  const autoBlocksBySlug = {}
  autoBlocks.forEach(block => {
    autoBlocksBySlug[block.slug] = reportBlockToStateBlock(block)
  })

  if (!(slug in autoBlocksBySlug)) {
    return state // no-op
  }

  return {
    ...state,
    workflow: {
      ...state.workflow,
      hasCustomReport: true,
      blockSlugs: autoBlocks.map(b => b.slug).filter(s => s !== slug)
    },
    blocks: removeByKey(autoBlocksBySlug, slug)
  }
}

function willReorder (oldSlugs, newSlugs) {
  if (oldSlugs.join('|') === newSlugs.join('|')) {
    return false // no-op
  }

  if (oldSlugs.splice().sort().join('|') !== newSlugs.splice().sort().join('|')) {
    return false // wrong newSlugs
  }

  return true
}

function reorderBlocksInCustomReport (state, slugs) {
  if (!willReorder(state.workflow.blockSlugs, slugs)) {
    return state
  }

  return {
    ...state,
    workflow: {
      ...state.workflow,
      blockSlugs: slugs
    }
  }
}

function reorderBlocksInAutoReport (state, slugs) {
  const autoBlocks = selectAutoReport(state)
  if (!willReorder(autoBlocks.map(b => b.slug), slugs)) {
    return state
  }

  const autoBlocksBySlug = {}
  autoBlocks.forEach(block => {
    autoBlocksBySlug[block.slug] = reportBlockToStateBlock(block)
  })
  return {
    ...state,
    workflow: {
      ...state.workflow,
      hasCustomReport: true,
      blockSlugs: slugs
    },
    blocks: autoBlocksBySlug
  }
}

export function addBlock (state, args) {
  const { slug, position, ...block } = args

  return state.workflow.hasCustomReport
    ? addBlockToCustomReport(state, slug, position, block)
    : addBlockToAutoReport(state, slug, position, block)
}

export function deleteBlock (state, args) {
  const { slug } = args
  return state.workflow.hasCustomReport
    ? deleteBlockFromCustomReport(state, slug)
    : deleteBlockFromAutoReport(state, slug)
}

export function reorderBlocks (state, args) {
  const { slugs } = args
  return state.workflow.hasCustomReport
    ? reorderBlocksInCustomReport(state, slugs)
    : reorderBlocksInAutoReport(state, slugs)
}

export function setBlockMarkdown (state, args) {
  const { slug, markdown } = args
  if (!(slug in state.blocks)) {
    return state
  }
  return {
    ...state,
    blocks: {
      ...state.blocks,
      [slug]: {
        ...state.blocks[slug],
        markdown
      }
    }
  }
}

const mutations = {
  [REPORT_ADD_BLOCK]: addBlock,
  [REPORT_DELETE_BLOCK]: deleteBlock,
  [REPORT_REORDER_BLOCKS]: reorderBlocks,
  [REPORT_SET_BLOCK_MARKDOWN]: setBlockMarkdown
}
export default mutations
