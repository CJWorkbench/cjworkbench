import * as util from './util'
import { generateSlug } from '../../utils'

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
    const { workflow } = getState()

    if (!workflow.tab_slugs.includes(slug)) {
      // This happens if the user clicks a "delete" button on the module:
      // 2. Browser dispatches "delete", which removes the tab
      // 1. Browser dispatches "click", which tries to select it
      // https://www.pivotaltracker.com/story/show/162803752
      return
    }

    // Only send API request if we're read-write
    const promise = workflow.read_only ? Promise.resolve(null) : api.setSelectedTab(slug)
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
    const name = util.generateTabName(new RegExp(util.escapeRegExp(tabPrefix) + ' (\\d+)'), tabPrefix + ' %d', tabNames)

    return dispatch({
      type: TAB_CREATE,
      payload: {
        promise: api.createTab(slug, name).then(() => ({ slug, name })),
        data: { slug, name, position: workflow.tab_slugs.length } // append
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

    return dispatch({
      type: TAB_DUPLICATE,
      payload: {
        promise: api.duplicateTab(oldSlug, slug, name).then(() => ({ slug, name })),
        data: {
          slug,
          name,
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
  const { workflow, pendingTabs } = state
  const { position, slug, name } = action.payload
  const tabSlugs = workflow.tab_slugs.slice() // shallow copy
  tabSlugs.splice(position, 0, slug)

  return {
    ...state,
    workflow: {
      ...workflow,
      tab_slugs: tabSlugs
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

  const newTabSlugs = [...workflow.tab_slugs]
  const deleteIndex = workflow.tab_slugs.indexOf(slug)
  newTabSlugs.splice(deleteIndex, 1)

  // If we're deleting the current tab, select the tab to its left; or if
  // there are none to the left, select the tab to the right. (Assume we never
  // delete the last tab.)
  let selectedPane = state.selectedPane
  if (selectedPane.pane === 'tab' && selectedPane.tabSlug === slug) {
    selectedPane = {
      pane: 'tab',
      tabSlug: deleteIndex === 0 ? newTabSlugs[0] : newTabSlugs[deleteIndex - 1]
    }
  }

  return {
    ...state,
    selectedPane,
    workflow: {
      ...workflow,
      tab_slugs: newTabSlugs,
      selected_tab_position: newTabSlugs.indexOf(selectedPane.tabSlug)
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
  const { workflow } = state
  const { slug } = action.payload

  return {
    ...state,
    selectedPane: { pane: 'tab', tabSlug: slug },
    workflow: {
      ...workflow,
      selected_tab_position: workflow.tab_slugs.indexOf(slug)
    }
  }
}

function reduceSetOrderPending (state, action) {
  const { tabSlugs } = action.payload
  const { workflow } = state

  // find new selected_tab_position. Ignore selectedPane: we aren't trying to
  // cause user-visible stuff here, we're only trying to predict what the
  // server will do.
  const tabSlug = workflow.tab_slugs[workflow.selected_tab_position]

  return {
    ...state,
    workflow: {
      ...workflow,
      tab_slugs: tabSlugs,
      selected_tab_position: tabSlugs.indexOf(tabSlug)
    }
  }
}

export const reducerFunctions = {
  [TAB_CREATE + '_PENDING']: reduceCreatePending,
  [TAB_DUPLICATE + '_PENDING']: reduceDuplicatePending,
  [TAB_DESTROY + '_PENDING']: reduceDestroyPending,
  [TAB_SET_NAME + '_PENDING']: reduceSetNamePending,
  [TAB_SELECT + '_PENDING']: reduceSelectPending,
  [TAB_SET_ORDER + '_PENDING']: reduceSetOrderPending
}
