import * as util from './util'

const TAB_SET_NAME = 'TAB_SET_NAME'
const TAB_DESTROY = 'TAB_DESTROY'
const TAB_CREATE = 'TAB_CREATE'
const TAB_SELECT = 'TAB_SELECT'
const TAB_SET_ORDER = 'TAB_SET_ORDER'

export function setName (tabId, name) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: TAB_SET_NAME,
      payload: {
        promise: api.setTabName(tabId, name),
        data: { tabId, name }
      }
    })
  }
}

export function setOrder (tabIds) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: TAB_SET_ORDER,
      payload: {
        promise: api.setTabOrder(tabIds),
        data: { tabIds }
      }
    })
  }
}

export function destroy (tabId) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: TAB_DESTROY,
      payload: {
        promise: api.deleteTab(tabId),
        data: { tabId }
      }
    })
  }
}

export function select (tabId) {
  return (dispatch, getState, api) => {
    dispatch({
      type: TAB_SELECT,
      payload: {
        promise: api.setSelectedTab(tabId),
        data: { tabId }
      }
    })
  }
}

export function create () {
  return (dispatch, getState, api) => {
    const { workflow, tabs } = getState()
    const tabNames = [ ...(workflow.pendingTabNames || []) ]
    for (const k in tabs) {
      tabNames.push(tabs[k].name)
    }

    const name = util.generateTabName(/Tab (\d+)/, 'Tab %d', tabNames)

    dispatch({
      type: TAB_CREATE,
      payload: {
        promise: api.createTab(name).then(() => ({ name })),
        data: { name }
      }
    })
  }
}

function reduceCreatePending (state, action) {
  const { workflow } = state
  const { name } = action.payload

  return {
    ...state,
    workflow: {
      ...workflow,
      pendingTabNames: [ ...(workflow.pendingTabNames || []), name ]
    }
  }
}

function reduceCreateFulfilled (state, action) {
  const { workflow } = state
  const { name } = action.payload

  const { pendingTabNames } = workflow
  const index = pendingTabNames.indexOf(name)

  if (index === -1) return state

  const newTabNames = pendingTabNames.slice()
  newTabNames.splice(index, 1)

  return {
    ...state,
    workflow: {
      ...workflow,
      pendingTabNames: newTabNames
    }
  }
}

function reduceDestroyPending (state, action) {
  const { tabId } = action.payload
  const { workflow, tabs } = state

  const newTabs = { ... tabs }
  delete newTabs[String(tabId)]

  const newTabIds = [ ... workflow.tab_ids ]
  const deleteIndex = workflow.tab_ids.indexOf(tabId)
  newTabIds.splice(deleteIndex, 1)

  const oldPosition = workflow.selected_tab_position
  let newPosition = (oldPosition < deleteIndex || oldPosition === 0) ? oldPosition : (oldPosition - 1)

  return {
    ...state,
    workflow: {
      ...workflow,
      tab_ids: newTabIds,
      selected_tab_position: newPosition
    },
    tabs: newTabs
  }
}

function reduceSetNamePending (state, action) {
  const { tabId, name } = action.payload
  const { tabs } = state
  const tab = tabs[String(tabId)]

  return {
    ...state,
    tabs: {
      ...tabs,
      [String(tabId)]: {
        ...tab,
        name
      }
    }
  }
}

function reduceSelectPending (state, action) {
  const { tabId } = action.payload
  const { workflow } = state

  return {
    ...state,
    workflow: {
      ...workflow,
      selected_tab_position: workflow.tab_ids.indexOf(tabId)
    }
  }
}

function reduceSetOrderPending (state, action) {
  const { tabIds } = action.payload
  const { workflow } = state

  const oldPosition = workflow.selected_tab_position
  const selectedTabId = workflow.tab_ids[oldPosition]
  const newPosition = tabIds.indexOf(selectedTabId)

  return {
    ...state,
    workflow: {
      ...workflow,
      tab_ids: tabIds,
      selected_tab_position: newPosition
    }
  }
}

export var reducerFunctions = {
  [TAB_CREATE + '_PENDING']: reduceCreatePending,
  [TAB_CREATE + '_FULFILLED']: reduceCreateFulfilled,
  [TAB_DESTROY + '_PENDING']: reduceDestroyPending,
  [TAB_SET_NAME + '_PENDING']: reduceSetNamePending,
  [TAB_SELECT + '_PENDING']: reduceSelectPending,
  [TAB_SET_ORDER + '_PENDING']: reduceSetOrderPending,
}
