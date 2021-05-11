export const TAB_CREATE = 'TAB_CREATE'
export const TAB_DESTROY = 'TAB_DESTROY'
export const TAB_SELECT = 'TAB_SELECT'
export const TAB_SET_NAME = 'TAB_SET_NAME'
export const TAB_SET_ORDER = 'TAB_SET_ORDER'

function createMutationCreator (type) {
  return ({ mutationId, ...args }) => ({ type, id: mutationId, args })
}

export const createCreateMutation = createMutationCreator(TAB_CREATE)
export const createDestroyMutation = createMutationCreator(TAB_DESTROY)
export const createSelectMutation = args => ({ type: TAB_SELECT, id: null, args })
export const createSetNameMutation = createMutationCreator(TAB_SET_NAME)
export const createSetOrderMutation = createMutationCreator(TAB_SET_ORDER)

function create (state, args) {
  const { slug, name, position } = args

  if (slug in state.tabs) {
    return state // no-op
  }

  const tabSlugs = state.workflow.tab_slugs.slice()
  if (position > tabSlugs.length) {
    return state // no-op
  }

  tabSlugs.splice(position, 0, slug)

  return {
    ...state,
    workflow: { ...state.workflow, tab_slugs: tabSlugs },
    tabs: { ...state.tabs, [slug]: { slug, name, step_ids: [], selected_step_position: null } }
  }
}

function destroy (state, args) {
  const { slug } = args

  const tabSlugs = state.workflow.tab_slugs
  const deleteIndex = tabSlugs.indexOf(slug)

  if (deleteIndex === -1) {
    return state // no-op
  }

  const newTabSlugs = tabSlugs.slice()
  newTabSlugs.splice(deleteIndex, 1)
  let selectedPane = state.selectedPane
  if (selectedPane.pane === 'tab' && selectedPane.tabSlug === slug) {
    selectedPane = {
      pane: 'tab',
      tabSlug: deleteIndex === 0 ? newTabSlugs[0] : newTabSlugs[deleteIndex - 1]
    }
  }

  const tabs = { ...state.tabs }
  delete tabs[slug]
  // We won't bother deleting steps. [2021-05-10] it may be more correct, but
  // so far we don't know what value it would provide.

  return {
    ...state,
    workflow: { ...state.workflow, tab_slugs: newTabSlugs },
    selectedPane,
    tabs
  }
}

function select (state, args) {
  const { slug } = args

  if (!state.workflow.tab_slugs.includes(slug)) {
    return state
  }

  return {
    ...state,
    selectedPane: { pane: 'tab', tabSlug: slug }
  }
}

function setName (state, args) {
  const { slug, name } = args
  if (!(slug in state.tabs)) {
    return state // no-op
  }

  return {
    ...state,
    tabs: {
      ...state.tabs,
      [slug]: {
        ...state.tabs[slug],
        name
      }
    }
  }
}

function setOrder (state, args) {
  const { tabSlugs } = args

  if (tabSlugs.slice().sort().join('|') !== state.workflow.tab_slugs.slice().sort().join('|')) {
    return state // no-op
  }

  return {
    ...state,
    workflow: {
      ...state.workflow,
      tab_slugs: tabSlugs
    }
  }
}

const mutations = {
  [TAB_CREATE]: create,
  [TAB_DESTROY]: destroy,
  [TAB_SELECT]: select,
  [TAB_SET_NAME]: setName,
  [TAB_SET_ORDER]: setOrder
}
export default mutations
