// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { createStore, applyMiddleware } from 'redux'

// Workflow
const UPDATE_MODULE = 'UPDATE_MODULE'
const ADD_MODULE = 'ADD_MODULE'
const DELETE_MODULE = 'DELETE_MODULE'
const SET_SELECTED_MODULE = 'SET_SELECTED_MODULE'
const SET_WORKFLOW_PUBLIC = 'SET_WORKFLOW_PUBLIC'
const MOVE_MODULE = 'MOVE_MODULE'

// Delta: workflow+wfmodule changes
const APPLY_DELTA = 'APPLY_DELTA'

// WfModule
const SET_WF_MODULE_STATUS = 'SET_WF_MODULE_STATUS'
const SET_WF_MODULE_COLLAPSED = 'SET_WF_MODULE_COLLAPSED'
const REQUEST_WF_MODULE_FETCH = 'REQUEST_WF_MODULE_FETCH'
const UPDATE_WF_MODULE = 'UPDATE_WF_MODULE'
const SET_WF_MODULE_PARAMS = 'SET_WF_MODULE_PARAMS'

// Data versions/notifications
const SET_DATA_VERSION = 'SET_DATA_VERSION'
const MARK_DATA_VERSIONS_READ = 'MARK_DATA_VERSIONS_READ'
const CLEAR_NOTIFICATIONS = 'CLEAR_NOTIFICATIONS'

// ---- Our Store ----
// Master state for the workflow.

const reducerFunc = {}

const registerReducerFunc = (key, func) => {
  reducerFunc[key] = func
}

let _nonce = 0
const generateNonce = (prefix) => {
  // Generate a nonce with some prefix from
  // the object we're creating the nonce for
  _nonce += 1
  return `${prefix}_${_nonce}`
}

// ---- Utilities for translating between ID and index ----

function findIdxByProp (searchArray, searchProp, searchValue) {
  let returnIdx
  for (let i = 0; i < searchArray.length; i++) {
    if (searchArray[i][searchProp] === searchValue) {
      returnIdx = i
      break
    }
  }
  return returnIdx
}

// ---- Actions ----

// -- Workflow actions --

/**
 * Given a Workflow from the server, modify it in-place, cancelling out any
 * server state that we're overwriting on the client.
 *
 * Currently, the only state we prevent the server from writing is
 * WfModule.is_collapsed.
 *
 * TODO get more formal about this; nix this method when we are.
 */
function omitWfModuleClientOnlyStateInPlace (wfModules, prevWfModules) {
  for (const key in wfModules) {
    const wfModule = wfModules[key]
    const prevWfModule = prevWfModules[key]
    if (!prevWfModule) continue
    wfModule.is_collapsed = prevWfModule.is_collapsed
  }
}

function moduleIdNameToModuleId (modules, idName) {
  const key = Object.keys(modules).find(m => modules[m].id_name === idName)
  if (!key) {
    alert(`Cannot find module "${idName}"`)
  }
  return Number(key)
}

// 'data' is { updateWorkflow, updateWfModules, updateTabs, clearWfModuleIds }, all
// optional
export function applyDeltaAction (data) {
  return { type: APPLY_DELTA, payload: data }
}
registerReducerFunc(APPLY_DELTA, (state, action) => {
  const data = action.payload

  let { workflow, wfModules, tabs } = state

  if (data.updateWorkflow) {
    const update = data.updateWorkflow
    delete update.selected_tab_position
    workflow = {
      ...workflow,
      ...update
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

  if (data.updateTabs || data.clearTabIds) {
    tabs = { ...tabs }

    for (const tabId in (data.updateTabs || {})) {
      const update = data.updateTabs[tabId]
      delete update.selected_wf_module_position
      tabs[tabId] = {
        ...tabs[tabId],
        ...update
      }
    }

    for (const tabId of (data.clearTabIds || [])) {
      delete tabs[String(tabId)]
    }
  }

  return {
    ...state,
    tabs,
    workflow,
    wfModules
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
    [String(module.id)]: module
  }

  return { ...state, modules }
})

// SET_WORKFLOW_PUBLIC
// Set the workflow to public or private
export function setWorkflowPublicAction (isPublic) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: SET_WORKFLOW_PUBLIC,
      payload: {
        promise: api.setWorkflowPublic(workflowId, isPublic),
        data: { isPublic }
      }
    })
  }
}
registerReducerFunc(SET_WORKFLOW_PUBLIC + '_PENDING', (state, action) => {
  const { isPublic } = action.payload
  return {
    ...state,
    workflow: {
      ...state.workflow,
      public: isPublic
    }
  }
})

// MOVE_MODULE
// Re-order the modules in the module stack
export function moveModuleAction (tabId, oldIndex, newIndex) {
  return (dispatch, getState, api) => {
    if (oldIndex < newIndex) {
      newIndex -= 1
    }

    const { workflow, tabs } = getState()
    const tab = tabs[String(tabId)]

    const newIds = tab.wf_module_ids.slice()
    newIds.splice(newIndex, 0, ...newIds.splice(oldIndex, 1))

    return dispatch({
      type: MOVE_MODULE,
      payload: {
        promise: api.reorderWfModules(workflow.id, newIds),
        data: {
          tabId,
          wfModuleIds: newIds
        }
      }
    })
  }
}
registerReducerFunc(MOVE_MODULE + '_PENDING', (state, action) => {
  let { tabId, wfModuleIds } = action.payload
  const tab = state.tabs[String(tabId)]

  return {
    ...state,
    tabs: {
      ...state.tabs,
      [String(tabId)]: {
        ...tab,
        wf_module_ids: wfModuleIds
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
 *                 * { tabId, index }
 *                 * { beforeWfModuleId }
 *                 * { afterWfModuleId }
 * @param parameterValues {id_name:value} Object of parameters for the
 *                        newly-created WfModule.
 */
export function addModuleAction (moduleId, position, parameterValues) {
  return (dispatch, getState, api) => {
    const { modules, tabs, wfModules, workflow } = getState()
    if (typeof moduleId === 'string' || moduleId instanceof String) {
      moduleId = moduleIdNameToModuleId(modules, moduleId)
    }
    const nonce = generateNonce(moduleId)

    let tabId, index

    if (position.tabId !== undefined && position.index !== undefined) {
      tabId = position.tabId
      index = position.index
    } else {
      const aWfModuleId = position.beforeWfModuleId || position.afterWfModuleId
      const aWfModule = wfModules[String(aWfModuleId)]
      tabId = aWfModule.tab_id
      const tab = tabs[String(tabId)]

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
          api.addModule(tabId, moduleId, index, parameterValues || {})
            .then(response => {
              return {
                tabId,
                nonce: nonce,
                data: response
              }
            })
        ),
        data: {
          tabId,
          index,
          nonce
        }
      }
    })
  }
}

registerReducerFunc(ADD_MODULE + '_PENDING', (state, action) => {
  const { tabs, workflow } = state
  const { tabId, index, nonce } = action.payload
  const tab = tabs[String(tabId)]
  const wfModuleIds = tab.wf_module_ids.slice()

  // Add a nonce to wf_modules Array of IDs. Don't add anything to wfModules:
  // users must assume that if it isn't in wfModules, it's a placeholder.
  wfModuleIds.splice(index, 0, nonce)

  return {
    ...state,
    tabs: {
      ...tabs,
      [String(tabId)]: {
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
  const tabId = wfModule.tab_id
  const tab = tabs[String(tabId)]

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
      [String(tabId)]: {
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
export function setSelectedWfModuleAction (wfModulePosition) {
  return (dispatch, getState, api) => {
    const { workflow, tabs } = getState()
    const tabPosition = 0  // TODO support other tabs
    const tabId = workflow.tab_ids[tabPosition]
    const tab = tabs[String(tabId)]

    if (
      workflow.selected_tab_position === tabPosition
      && tab.selected_wf_module_position === wfModulePosition
    ) {
      // avoid spurious HTTP requests and state changes
      return
    }

    // Fire-and-forget: tell the server about this new selection
    // so next time we load the page it will pass it in initState.
    api.setSelectedWfModule(workflow.id, wfModulePosition)
      .catch(console.warn)

    return dispatch({
      type: SET_SELECTED_MODULE,
      payload: { tabPosition, tabId, wfModulePosition }
    })
  }
}
registerReducerFunc(SET_SELECTED_MODULE, (state, action) => {
  const { workflow, tabs } = state
  const { tabPosition, tabId, wfModulePosition } = action.payload
  const tab = tabs[String(tabId)]

  return {
    ...state,
    workflow: {
      ...workflow,
      selected_tab_position: tabPosition
    },
    tabs: {
      ...tabs,
      [String(tabId)]: {
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
    const { workflow, wfModules } = getState()
    const wfModule = wfModules[String(wfModuleId)]
    const hasVersionSelect = !!wfModule.parameter_vals.find(pv => pv.parameter_spec.id_name === 'version_select')

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

  // Copy parameter_vals, setting new values based on params.
  const paramVals = wfModule.parameter_vals.map(pv => {
    const id_name = pv.parameter_spec.id_name
    if (id_name in params) {
      return { ...pv, value: params[id_name] }
    } else {
      return pv
    }
  })

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        parameter_vals: paramVals
      }
    }
  }
})

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

// MARK_DATA_VERSIONS_READ
// Called when the user views a version that has a "new data" alert on it
export function markDataVersionsReadAction (wfModuleId, versions) {
  return (dispatch, getState, api) => {
    const { workflow } = getState()

    let versionsToUpdate = [].concat(versions) // will accept one or many
    return dispatch({
      type: MARK_DATA_VERSIONS_READ,
      payload: {
        promise: api.markDataVersionsRead(wfModuleId, versionsToUpdate),
        data: {
          wfModuleId,
          versionsToUpdate
        }
      }
    })
  }
}
registerReducerFunc(MARK_DATA_VERSIONS_READ + '_PENDING', (state, action) => {
  const { wfModuleId, versionsToUpdate } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule) return state
  if (!wfModule.versions) return state

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        versions: { ...wfModule.versions,
          versions: wfModule.versions.versions.map(version => {
            // If this is a version we want to mark read,
            if (versionsToUpdate.includes(version[0])) {
              // Set the 'read' bit to true
              return [ version[0], true ]
            } else {
              // Return the version
              return version
            }
          })
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

function quickFixPrependModule(wfModuleId, moduleIdName, parameterValues) {
  return addModuleAction(moduleIdName, { beforeWfModuleId: wfModuleId }, parameterValues)
}

export function quickFixAction(action, wfModuleId, args) {
  return {
    prependModule: quickFixPrependModule
  }[action](wfModuleId, ...args)
}

// ---- Reducer ----
// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion

export function workflowReducer (state, action) {
  if (!state) {
    state = {} // initial state. we'll load a workflow soon.
  }

  if (reducerFunc && action.type in reducerFunc) {
    return reducerFunc[action.type](state, action)
  }

  return state
}
