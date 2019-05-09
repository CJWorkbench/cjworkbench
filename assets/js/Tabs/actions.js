import * as util from './util'
import { generateSlug } from '../utils'

const TAB_SET_NAME = 'TAB_SET_NAME'
const TAB_DESTROY = 'TAB_DESTROY'
const TAB_CREATE = 'TAB_CREATE'
const TAB_DUPLICATE = 'TAB_DUPLICATE'
const TAB_SELECT = 'TAB_SELECT'
const TAB_SET_ORDER = 'TAB_SET_ORDER'

export function setName (slug, name) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: TAB_SET_NAME,
      payload: {
        promise: api.setTabName(slug, name),
        data: { slug, name }
      }
    })
  }
}

export function setOrder (tabSlugs) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: TAB_SET_ORDER,
      payload: {
        promise: api.setTabOrder(tabSlugs),
        data: { tabSlugs }
      }
    })
  }
}

export function destroy (slug) {
  return (dispatch, getState, api) => {
    if (getState().workflow.tab_slugs.length === 1) {
      return
    }

    return dispatch({
      type: TAB_DESTROY,
      payload: {
        promise: api.deleteTab(slug),
        data: { slug }
      }
    })
  }
}

export function select (slug) {
  return (dispatch, getState, api) => {
    if (!getState().workflow.tab_slugs.includes(slug)) {
      // This happens if the user clicks a "delete" button on the module:
      // 2. Browser dispatches "delete", which removes the tab
      // 1. Browser dispatches "click", which tries to select it
      // https://www.pivotaltracker.com/story/show/162803752
      return
    }

    dispatch({
      type: TAB_SELECT,
      payload: {
        promise: api.setSelectedTab(slug),
        data: { slug }
      }
    })
  }
}

export function create () {
  return (dispatch, getState, api) => {
    const state = getState()
    const { workflow, tabs } = state
    const pendingTabs = state.pendingTabs || {}

    const tabNames = []
    for (const k in tabs) {
      tabNames.push(tabs[k].name)
    }
    for (const k in pendingTabs) {
      tabNames.push(pendingTabs[k].name)
    }

    const slug = generateSlug('tab-')
    const name = util.generateTabName(/Tab (\d+)/, 'Tab %d', tabNames)

    dispatch({
      type: TAB_CREATE,
      payload: {
        promise: api.createTab(slug, name).then(() => ({ slug, name })),
        data: { slug, name }
      }
    })
  }
}

export function duplicate (oldSlug) {
  return (dispatch, getState, api) => {
    const state = getState()
    const { workflow, tabs } = state
    const pendingTabs = state.pendingTabs || {}

    const tabNames = []
    for (const k in tabs) {
      tabNames.push(tabs[k].name)
    }
    for (const k in pendingTabs) {
      tabNames.push(pendingTabs[k].name)
    }

    const oldTab = tabs[oldSlug]
    const oldNameBase = oldTab.name.replace(/ \((\d+)\)$/, '')
    const slug = generateSlug('tab-')
    const nameRegex = new RegExp(util.escapeRegExp(oldNameBase) + ' \\((\\d+)\\)')
    const namePattern = oldNameBase + ' (%d)'
    const name = util.generateTabName(nameRegex, namePattern, tabNames)

    dispatch({
      type: TAB_DUPLICATE,
      payload: {
        promise: api.duplicateTab(oldSlug, slug, name).then(() => ({ slug, name })),
        data: { slug, name }
      }
    })
  }
}

function reduceCreatePending (state, action) {
  const { pendingTabs, workflow } = state
  const { slug, name } = action.payload

  return {
    ...state,
    workflow: {
      ...workflow,
      tab_slugs: [ ...workflow.tab_slugs, slug ]
    },
    pendingTabs: {
      ...pendingTabs,
      [slug]: {
        slug,
        name,
        wf_module_ids: [],
        selected_wf_module_position: null
      }
    }
  }
}

const reduceDuplicatePending = reduceCreatePending

function reduceDestroyPending (state, action) {
  const { slug } = action.payload
  const { workflow, tabs } = state
  const pendingTabs = state.pendingTabs || {}

  const newTabs = { ...tabs }
  delete newTabs[slug]

  const newPendingTabs = { ...pendingTabs }
  delete newPendingTabs[slug]

  const newTabSlugs = [ ...workflow.tab_slugs ]
  const deleteIndex = workflow.tab_slugs.indexOf(slug)
  newTabSlugs.splice(deleteIndex, 1)

  const oldPosition = workflow.selected_tab_position
  const newPosition = (oldPosition < deleteIndex || oldPosition === 0) ? oldPosition : (oldPosition - 1)

  return {
    ...state,
    workflow: {
      ...workflow,
      tab_slugs: newTabSlugs,
      selected_tab_position: newPosition
    },
    pendingTabs: newPendingTabs,
    tabs: newTabs
  }
}

function reduceSetNamePending (state, action) {
  const { slug, name } = action.payload
  const { tabs } = state
  const tab = tabs[slug]

  return {
    ...state,
    tabs: {
      ...tabs,
      [slug]: {
        ...tab,
        name
      }
    }
  }
}

function reduceSelectPending (state, action) {
  const { slug } = action.payload
  const { workflow } = state

  return {
    ...state,
    workflow: {
      ...workflow,
      selected_tab_position: workflow.tab_slugs.indexOf(slug)
    }
  }
}

function reduceSetOrderPending (state, action) {
  const { tabSlugs } = action.payload
  const { workflow } = state

  const oldPosition = workflow.selected_tab_position
  const selectedTabSlug = workflow.tab_slugs[oldPosition]
  const newPosition = tabSlugs.indexOf(selectedTabSlug)

  return {
    ...state,
    workflow: {
      ...workflow,
      tab_slugs: tabSlugs,
      selected_tab_position: newPosition
    }
  }
}

export var reducerFunctions = {
  [TAB_CREATE + '_PENDING']: reduceCreatePending,
  [TAB_DUPLICATE + '_PENDING']: reduceDuplicatePending,
  [TAB_DESTROY + '_PENDING']: reduceDestroyPending,
  [TAB_SET_NAME + '_PENDING']: reduceSetNamePending,
  [TAB_SELECT + '_PENDING']: reduceSelectPending,
  [TAB_SET_ORDER + '_PENDING']: reduceSetOrderPending,
}
