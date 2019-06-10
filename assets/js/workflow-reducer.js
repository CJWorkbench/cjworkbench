// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { createStore, applyMiddleware } from 'redux'
import { reducerFunctions as TabReducerFunctions } from './WorkflowEditor/Tabs/actions'
import { reducerFunctions as WorkflowEditorReducerFunctions } from './WorkflowEditor/actions'
import { reducerFunctions as ShareReducerFunctions } from './ShareModal/actions'
import { reducerFunctions as FileReducerFunctions } from './params/File/actions'
import { UNHANDLED_ERROR } from './error-middleware'

// Workflow
const SET_WORKFLOW_NAME = 'SET_WORKFLOW_NAME'
const UPDATE_MODULE = 'UPDATE_MODULE'
const ADD_MODULE = 'ADD_MODULE'
const DELETE_MODULE = 'DELETE_MODULE'
const SET_SELECTED_MODULE = 'SET_SELECTED_MODULE'
const MOVE_MODULE = 'MOVE_MODULE'

// Delta: workflow+wfmodule changes
const APPLY_DELTA = 'APPLY_DELTA'

// WfModule
const SET_WF_MODULE_NOTES = 'SET_WF_MODULE_NOTES'
const SET_WF_MODULE_STATUS = 'SET_WF_MODULE_STATUS'
const SET_WF_MODULE_COLLAPSED = 'SET_WF_MODULE_COLLAPSED'
const REQUEST_WF_MODULE_FETCH = 'REQUEST_WF_MODULE_FETCH'
const UPDATE_WF_MODULE = 'UPDATE_WF_MODULE'
const SET_WF_MODULE_PARAMS = 'SET_WF_MODULE_PARAMS'
const SET_WF_MODULE_SECRET = 'SET_WF_MODULE_SECRET'

// Data versions/notifications
const SET_DATA_VERSION = 'SET_DATA_VERSION'
const CLEAR_NOTIFICATIONS = 'CLEAR_NOTIFICATIONS'

// ---- Our Store ----
// Master state for the workflow.

/**
 * Reduce using an "error" FSA.
 *
 * Action is `{ error: true, type: [original action type], payload: <Error>}`
 *
 * Ensures `state.firstUnhandledError` looks like `{type, message, serverError}`
 * (all String).
 */
function handleError (state, action) {
  console.warn('Unhandled error during %s dispatch', action.type, action.payload)

  if (state.firstUnhandledError) {
    return state
  } else {
    const err = action.payload
    return {
      ...state,
      firstUnhandledError: {
        type: action.type,
        message: err.toString(),
        serverError: err.serverError || null
      }
    }
  }
}

const reducerFunc = {
  ...FileReducerFunctions,
  ...ShareReducerFunctions,
  ...TabReducerFunctions,
  ...WorkflowEditorReducerFunctions
}

const registerReducerFunc = (key, func) => {
  reducerFunc[key] = func
}

function generateNonce (invalidValues, prefix) {
  for (let i = 0; true; i++) {
    const attempt = `nonce-${prefix}-${i}`
    if (!(attempt in invalidValues)) {
      return attempt
    }
  }
}

// -- Workflow actions --

// 'data' is { updateWorkflow, updateWfModules, updateTabs, clearTabSlugs, clearWfModuleIds }, all
// optional
export function applyDeltaAction (data) {
  return { type: APPLY_DELTA, payload: data }
}
registerReducerFunc(APPLY_DELTA, (state, action) => {
  const data = action.payload

  let { workflow, wfModules, tabs, pendingTabs } = state

  if (data.updateWorkflow) {
    workflow = {
      ...workflow,
      ...data.updateWorkflow
    }
  }

  if (data.updateWfModules || data.clearWfModuleIds) {
    wfModules = { ...wfModules }

    if (data.updateWfModules) {
      for (const wfModuleId in (data.updateWfModules || {})) {
        wfModules[wfModuleId] = {
          ...wfModules[wfModuleId],
          ...data.updateWfModules[wfModuleId]
        }
      }
    }

    if (data.clearWfModuleIds) {
      wfModules = { ...wfModules }
      for (const wfModuleId of (data.clearWfModuleIds || [])) {
        delete wfModules[String(wfModuleId)]
      }
    }
  }

  if (data.updateTabs || data.clearTabSlugs) {
    tabs = { ...tabs }
    pendingTabs = { ...(pendingTabs || {}) } // shallow copy

    for (const tabSlug in (data.updateTabs || {})) {
      const update = data.updateTabs[tabSlug]
      const oldPosition = tabs[tabSlug] ? tabs[tabSlug].selected_wf_module_position : null
      tabs[tabSlug] = {
        ...tabs[tabSlug],
        ...update
      }
      if (oldPosition !== null) {
        // Server updates shouldn't overwrite selected_wf_module_position ...
        // _except_ if the client doesn't actually have a position set (such as
        // when duplicate succeeds and the new tab is one we haven't seen).
        tabs[tabSlug].selected_wf_module_position = oldPosition
      }
      delete pendingTabs[tabSlug] // if it's a pendingTab
    }

    for (const tabSlug of (data.clearTabSlugs || [])) {
      delete tabs[tabSlug]
      delete pendingTabs[tabSlug]
    }
  }

  return {
    ...state,
    tabs,
    pendingTabs,
    workflow,
    wfModules
  }
})

// SET_WORKFLOW_NAME
// Set name of workflow
export function setWorkflowNameAction (name) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: SET_WORKFLOW_NAME,
      payload: {
        promise: api.setWorkflowName(name),
        data: { name }
      }
    })
  }
}
registerReducerFunc(SET_WORKFLOW_NAME + '_PENDING', (state, action) => {
  const { name } = action.payload
  return {
    ...state,
    workflow: {
      ...state.workflow,
      name
    }
  }
})

// UPDATE_MODULE
// Write or rewrite a module in state.modules
export function updateModuleAction (module) {
  return {
    type: UPDATE_MODULE,
    payload: { module }
  }
}
registerReducerFunc(UPDATE_MODULE, (state, action) => {
  const { module } = action.payload

  const modules = {
    ...state.modules,
    [String(module.id_name)]: module
  }

  return { ...state, modules }
})

// MOVE_MODULE
// Re-order the modules in the module stack
export function moveModuleAction (tabSlug, oldIndex, newIndex) {
  return (dispatch, getState, api) => {
    if (oldIndex < newIndex) {
      newIndex -= 1
    }

    const { workflow, tabs } = getState()
    const tab = tabs[tabSlug]

    const newIds = tab.wf_module_ids.slice()
    newIds.splice(newIndex, 0, ...newIds.splice(oldIndex, 1))

    return dispatch({
      type: MOVE_MODULE,
      payload: {
        promise: api.reorderWfModules(tabSlug, newIds),
        data: {
          tabSlug,
          wfModuleIds: newIds
        }
      }
    })
  }
}
registerReducerFunc(MOVE_MODULE + '_PENDING', (state, action) => {
  const { tabSlug, wfModuleIds } = action.payload
  const tab = state.tabs[tabSlug]

  const oldIndex = tab.selected_wf_module_position
  const oldId = tab.wf_module_ids[oldIndex]
  const newIndex = wfModuleIds.indexOf(oldId)

  return {
    ...state,
    tabs: {
      ...state.tabs,
      [tabSlug]: {
        ...tab,
        wf_module_ids: wfModuleIds,
        selected_wf_module_position: newIndex
      }
    }
  }
})

// ADD_MODULE
/**
 * Add a placeholder (phony String WfModule ID) to tab.wf_module_ids and
 * send an API request to add the module; on completion, add to wfModules and
 * replace the placeholder in tab.wf_module_ids with the new wfModule ID.
 *
 * Parameters:
 * @param moduleId String module id_name or Number module ID.
 * @param position Object position this module should be in. One of:
 *                 * { tabSlug, index }
 *                 * { beforeWfModuleId }
 *                 * { afterWfModuleId }
 * @param parameterValues {idName:value} Object of parameters for the
 *                        newly-created WfModule.
 */
export function addModuleAction (moduleIdName, position, parameterValues) {
  return (dispatch, getState, api) => {
    const { modules, tabs, wfModules, workflow } = getState()
    const nonce = generateNonce(wfModules, moduleIdName)

    let tabSlug, index

    if (position.tabSlug !== undefined && position.index !== undefined) {
      tabSlug = position.tabSlug
      index = position.index
    } else {
      const aWfModuleId = position.beforeWfModuleId || position.afterWfModuleId
      const aWfModule = wfModules[String(aWfModuleId)]
      tabSlug = aWfModule.tab_slug
      const tab = tabs[tabSlug]

      if (position.beforeWfModuleId) {
        const previous = tab.wf_module_ids.indexOf(position.beforeWfModuleId)
        if (previous === -1) {
          console.warn('Ignoring addModuleAction with invalid position', position)
          return
        }
        index = previous
      }
      if (position.afterWfModuleId) {
        const previous = tab.wf_module_ids.indexOf(position.afterWfModuleId)
        if (previous === -1) {
          console.warn('Ignoring addModuleAction with invalid position', position)
          return
        }
        index = previous + 1
      }
    }

    return dispatch({
      type: ADD_MODULE,
      payload: {
        promise: (
          api.addModule(tabSlug, moduleIdName, index, parameterValues || {})
            .then(response => {
              return {
                tabSlug,
                nonce: nonce,
                data: response
              }
            })
        ),
        data: {
          tabSlug,
          index,
          nonce
        }
      }
    })
  }
}

registerReducerFunc(ADD_MODULE + '_PENDING', (state, action) => {
  const { tabs, workflow } = state
  const { tabSlug, index, nonce } = action.payload
  const tab = tabs[tabSlug]
  const wfModuleIds = tab.wf_module_ids.slice()

  // Add a nonce to wf_modules Array of IDs. Don't add anything to wfModules:
  // users must assume that if it isn't in wfModules, it's a placeholder.
  wfModuleIds.splice(index, 0, nonce)

  return {
    ...state,
    tabs: {
      ...tabs,
      [tabSlug]: {
        ...tab,
        wf_module_ids: wfModuleIds,
        selected_wf_module_position: index
      }
    }
  }
})

// DELETE_MODULE_ACTION
// Call delete API, then dispatch a reload
export function deleteModuleAction (wfModuleId) {
  return (dispatch, getState, api) => {
    const { workflow } = getState()

    return dispatch({
      type: DELETE_MODULE,
      payload: {
        promise: api.deleteModule(wfModuleId),
        data: { wfModuleId }
      }
    })
  }
}
registerReducerFunc(DELETE_MODULE + '_PENDING', (state, action) => {
  const { wfModuleId } = action.payload

  const { tabs, wfModules } = state
  const wfModule = wfModules[String(wfModuleId)]
  const tab = tabs[wfModule.tab_slug]

  const wfModuleIds = tab.wf_module_ids.slice()
  const index = wfModuleIds.indexOf(wfModuleId)
  if (index === -1) return state

  wfModuleIds.splice(index, 1)

  const newWfModules = { ... state.wfModules }
  delete newWfModules[String(wfModuleId)]

  // If we are deleting the selected module, then set the previous module
  // in stack as selected
  let selected = tab.selected_wf_module_position
  if (selected !== null && selected >= index) {
    selected -= 1
  }
  if (selected < 0) {
    selected = 0
  }
  if (!Object.keys(newWfModules).length) {
    selected = null
  }

  return {
    ...state,
    tabs: {
      ...tabs,
      [tab.slug]: {
        ...tab,
        wf_module_ids: wfModuleIds,
        selected_wf_module_position: selected
      }
    },
    wfModules: newWfModules
  }
})

// SET_SELECTED_MODULE
// Set the selected module in the workflow
export function setSelectedWfModuleAction (wfModuleId) {
  return (dispatch, getState, api) => {
    const { workflow, tabs, wfModules } = getState()

    const wfModule = wfModules[String(wfModuleId)]
    if (!wfModule) return

    const tabSlug = wfModule.tab_slug
    const tab = tabs[tabSlug]

    const tabPosition = workflow.tab_slugs.indexOf(tabSlug)
    const wfModulePosition = tab.wf_module_ids.indexOf(wfModuleId)

    if (
      workflow.selected_tab_position === tabPosition
      && tab.selected_wf_module_position === wfModulePosition
    ) {
      // avoid spurious HTTP requests and state changes
      return
    }

    // Fire-and-forget: tell the server about this new selection
    // so next time we load the page it will pass it in initState.
    const promise = workflow.read_only ? Promise.resolve(null) : api.setSelectedWfModule(wfModuleId)
    return dispatch({
      type: SET_SELECTED_MODULE,
      payload: {
        promise,
        data: {tabPosition, tabSlug, wfModulePosition }
      }
    })
  }
}
registerReducerFunc(SET_SELECTED_MODULE + '_PENDING', (state, action) => {
  const { workflow, tabs } = state
  const { tabPosition, tabSlug, wfModulePosition } = action.payload
  const tab = tabs[tabSlug]

  return {
    ...state,
    selectedPane: { // so we navigate to the WfModule
      pane: 'tab',
      tabSlug
    },
    workflow: {
      ...workflow,
      selected_tab_position: tabPosition // so we don't POST spurious updates
    },
    tabs: {
      ...tabs,
      [tabSlug]: {
        ...tab,
        selected_wf_module_position: wfModulePosition
      }
    }
  }
})

// --- Workflow Module actions ---

/*
 * Tell the server to reload data from upstream.
 *
 * Only works if there is a 'version_select' custom parameter.
 */
export function maybeRequestWfModuleFetchAction (wfModuleId) {
  return (dispatch, getState, api) => {
    const { workflow, wfModules, modules } = getState()
    const wfModule = wfModules[String(wfModuleId)]
    const module = wfModule.module ? modules[wfModule.module] : null
    const hasVersionSelect = module ? !!module.param_fields.find(ps => ps.idName === 'version_select') : null

    if (!hasVersionSelect) return

    return dispatch({
      type: REQUEST_WF_MODULE_FETCH,
      payload: {
        promise: api.requestFetch(wfModuleId)
          .then(() => ({ wfModuleId }), (err) => { console.warn(err); return { wfModuleId } }),
        data: { wfModuleId }
      }
    })
  }
}

registerReducerFunc(REQUEST_WF_MODULE_FETCH + '_PENDING', (state, action) => {
  const { wfModuleId } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]

  // Set the WfModule to 'busy' on the client side.
  //
  // Don't conflict with the server side: use a client-specific variable.
  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        nClientRequests: (wfModule.nClientRequests || 0) + 1
      }
    }
  }
})

registerReducerFunc(REQUEST_WF_MODULE_FETCH + '_FULFILLED', (state, action) => {
  const { wfModuleId } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]

  if (!wfModule) return

  // Set the WfModule to 'busy' on the client side.
  //
  // A fetch might cause _all_ WfModules to become busy on the server, if it
  // kicks off a ChangeDataVersionCommand. If it doesn't, the other WfModules
  // will stay as they are. Let's not pre-emptively update those _other_
  // WfModule statuses, lest the server never tell us they won't change.
  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        nClientRequests: (wfModule.nClientRequests || 1) - 1
      }
    }
  }
})


// UPDATE_WF_MODULE
// Patch a workflow module with new data

// TODO: We don't validate which fields or types are on
// a WfModule here. The server will reject nonexistent
// fields, but should we show the user an error?
export function updateWfModuleAction (wfModuleId, data) {
  return (dispatch, getState, api) => {
    const { workflow, wfModules } = getState()

    if (!wfModules[String(wfModuleId)]) return Promise.resolve(null)

    return dispatch({
      type: UPDATE_WF_MODULE,
      payload: {
        promise: api.updateWfModule(wfModuleId, data),
        data: {
          wfModuleId,
          data
        }
      }
    })
  }
}
registerReducerFunc(UPDATE_WF_MODULE + '_PENDING', (state, action) => {
  const { wfModuleId, data } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        ...data
      }
    }
  }
})

export function setWfModuleNotesAction (wfModuleId, notes) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: SET_WF_MODULE_NOTES,
      payload: {
        promise: api.setWfModuleNotes(wfModuleId, notes),
        data: { wfModuleId, notes }
      }
    })
  }
}
registerReducerFunc(SET_WF_MODULE_NOTES + '_PENDING', (state, action) => {
  const { wfModuleId, notes } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]
  if (wfModule) {
    return {
      ...state,
      wfModules: {
        ...state.wfModules,
        [String(wfModuleId)]: {
          ...wfModule,
          notes
        }
      }
    }
  } else {
    return state
  }
})

// SET_WF_MODULE_STATUS
// Change the workflow status (OK, pending, error)
//
// TODO nix this. It's always wrong. The _server_ decides when a module is busy.
export function setWfModuleBusyAction (wfModuleId) {
  return {
    type: SET_WF_MODULE_STATUS,
    payload: {
      wfModuleId,
    }
  }
}
registerReducerFunc(SET_WF_MODULE_STATUS, (state, action) => {
  const { wfModuleId } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule) return state

  if (wfModule.is_busy) {
    return state
  }

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        is_busy: True,
        fetch_error: ''
      }
    }
  }
})

export function setWfModuleCollapsedAction (wfModuleId, isCollapsed, isReadOnly) {
  return (dispatch, getState, api) => {
    let promise
    if (isReadOnly) {
      promise = Promise.resolve(null)
    } else {
      const { workflow } = getState()
      promise = api.setWfModuleCollapsed(wfModuleId, isCollapsed)
    }

    return dispatch({
      type: SET_WF_MODULE_COLLAPSED,
      payload: {
        promise,
        data: {
          wfModuleId,
          isCollapsed
        }
      }
    })
  }
}
registerReducerFunc(SET_WF_MODULE_COLLAPSED + '_PENDING', (state, action) => {
  const { wfModuleId, isCollapsed } = action.payload
  const wfModule = state.wfModules[wfModuleId]
  if (!wfModule) return state

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        is_collapsed: isCollapsed
      }
    }
  }
})

export function setWfModuleParamsAction (wfModuleId, params) {
  return (dispatch, getState, api) => {
    const { workflow } = getState()

    return dispatch({
      type: SET_WF_MODULE_PARAMS,
      payload: {
        promise: api.setWfModuleParams(wfModuleId, params),
        data: {
          wfModuleId,
          params
        }
      }
    })
  }
}

registerReducerFunc(SET_WF_MODULE_PARAMS + '_PENDING', (state, action) => {
  const { wfModuleId, params } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        params: {
          ...wfModule.params,
          ...params
        }
      }
    }
  }
})

export function setWfModuleSecretAction (wfModuleId, param, secret) {
  return (dispatch, getState, api) => {
    const { workflow } = getState()

    return dispatch({
      type: SET_WF_MODULE_SECRET,
      payload: {
        promise: api.setSecret(wfModuleId, param, secret),
        data: {
          wfModuleId,
          param
        }
      }
    })
  }
}


// --- Data Version actions ---

// SET_DATA_VERSION
export function setDataVersionAction (wfModuleId, selectedVersion) {
  return (dispatch, getState, api) => {
    const { workflow } = getState()

    return dispatch({
      type: SET_DATA_VERSION,
      payload: {
        promise: api.setWfModuleVersion(wfModuleId, selectedVersion),
        data: {
          wfModuleId,
          selectedVersion
        }
      }
    })
  }
}
registerReducerFunc(SET_DATA_VERSION + '_PENDING', (state, action) => {
  const { wfModuleId, selectedVersion } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule) return state

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        versions: { ...wfModule.versions,
          selected: selectedVersion
        }
      }
    }
  }
})

export function clearNotificationsAction (wfModuleId) {
  return (dispatch, getState, api) => {
    const { workflow } = getState()

    return dispatch({
      type: CLEAR_NOTIFICATIONS,
      payload: {
        promise: api.deleteWfModuleNotifications(wfModuleId),
        data: {
          wfModuleId
        }
      }
    })
  }
}
registerReducerFunc(CLEAR_NOTIFICATIONS + '_PENDING', (state, action) => {
  const { wfModuleId } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule) return state

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        has_unseen_notification: false
      }
    }
  }
})

export function startCreateSecretAction (wfModuleId, param) {
  return (dispatch, getState, api) => {
    const workflowId = getState().workflow.id
    api.startCreateSecret(workflowId, wfModuleId, param)
  }
}

export function deleteSecretAction (wfModuleId, param) {
  return (dispatch, getState, api) => {
    // TODO consider modifying state. Right now we don't. When the user clicks
    // "sign out", we only show feedback after the server has deleted the param
    // and sent a delta. Maybe that's actually what we want?.... Or maybe we
    // need immediate feedback in
    // the state.
    api.deleteSecret(wfModuleId, param)
  }
}

function quickFixPrependModule(wfModuleId, moduleIdName, parameterValues) {
  return addModuleAction(moduleIdName, { beforeWfModuleId: wfModuleId }, parameterValues)
}

export function quickFixAction(wfModuleId, action, args) {
  return {
    prependModule: quickFixPrependModule
  }[action](wfModuleId, ...args)
}

// ---- Reducer ----
// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion

export function workflowReducer (state={}, action) {
  if (action.error === true) {
    return handleError(state, action)
  }

  if (action.type in reducerFunc) {
    // Run a registered reducer
    return reducerFunc[action.type](state, action)
  }

  return state
}
