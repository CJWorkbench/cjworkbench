// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { createStore, applyMiddleware, compose } from 'redux'
import promiseMiddleware from 'redux-promise-middleware'
import thunk from 'redux-thunk'
import { newContext } from 'immutability-helper'
import api from './WorkbenchAPI'

// Workflow
const RELOAD_WORKFLOW = 'RELOAD_WORKFLOW'
const SET_WORKFLOW = 'SET_WORKFLOW'
const LOAD_MODULES = 'LOAD_MODULES'
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
const SET_WF_MODULE = 'SET_WF_MODULE'
const SET_WF_MODULE_PARAMS = 'SET_WF_MODULE_PARAMS'

// Parameter
const SET_PARAM_VALUE = 'SET_PARAM_VALUE'

// Data versions/notifications
const SET_DATA_VERSION = 'SET_DATA_VERSION'
const MARK_DATA_VERSIONS_READ = 'MARK_DATA_VERSIONS_READ'
const CLEAR_NOTIFICATIONS = 'CLEAR_NOTIFICATIONS'

// ---- Our Store ----
// Master state for the workflow.
const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose

export const middlewares = [ promiseMiddleware(), thunk ]

// TODO do not export store! It makes tests _and_ code hard to write, for zero value gain
export var store = createStore(
  workflowReducer,
  window.initState,
  composeEnhancers(applyMiddleware(...middlewares))
)

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

const update = newContext()
update.extend('$reorder', function (value, original) {
  const [oldIndex, newIndex] = value
  const newArray = original.slice()
  newArray.splice(newIndex, 0, newArray.splice(oldIndex, 1)[0])
  return newArray
})

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

// RELOAD_WORKFLOW
// Re-load the workflow
export function reloadWorkflowAction () {
  return (dispatch, getState) => {
    return dispatch({
      type: RELOAD_WORKFLOW,
      payload: api.loadWorkflow(getState().workflow.id)
    })
  }
}
registerReducerFunc(RELOAD_WORKFLOW + '_FULFILLED', (state, action) => {
  const { workflow, wfModules } = action.payload

  omitWfModuleClientOnlyStateInPlace(wfModules, state.wfModules)

  return { ...state, workflow, wfModules }
})

// 'data' is { workflow, wfModules } ... but wfModules is optional
export function setWorkflowAction (data) {
  return { type: SET_WORKFLOW, payload: data }
}
registerReducerFunc(SET_WORKFLOW, (state, action) => {
  return {
    ...state,
    ...action.payload
  }
})

// 'data' is { updateWorkflow, updateWfModules, clearWfModuleIds }, all
// optional
export function applyDeltaAction (data) {
  return { type: APPLY_DELTA, payload: data }
}
registerReducerFunc(APPLY_DELTA, (state, action) => {
  const data = action.payload

  let workflow = state.workflow
  if (data.updateWorkflow) {
    workflow = {
      ...workflow,
      ...data.updateWorkflow
    }
  }

  let wfModules = state.wfModules
  if (data.updateWfModules) {
    wfModules = { ...wfModules }
    for (const wfModuleId in data.updateWfModules) {
      wfModules[wfModuleId] = {
        ...wfModules[wfModuleId],
        ...data.updateWfModules[wfModuleId]
      }
    }
  }

  if (data.clearWfModuleIds) {
    wfModules = { ...wfModules }
    for (const wfModuleId of data.clearWfModuleIds) {
      delete wfModules[String(wfModuleId)]
    }
  }

  return {
    ...state,
    workflow,
    wfModules
  }
})

// LOAD_MODULES
// Populate/refresh the module library
export function loadModulesAction () {
  return {
    type: LOAD_MODULES,
    payload: api.getModules()
  }
}
registerReducerFunc(LOAD_MODULES + '_FULFILLED', (state, action) => {
  const modulesArray = action.payload
  const modules = {}
  for (const module of modulesArray) {
    modules[String(module.id)] = module
  }

  return { ...state, modules }
})

// SET_WORKFLOW_PUBLIC
// Set the workflow to public or private
export function setWorkflowPublicAction (workflowId, isPublic) {
  return (dispatch) => {
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
export function moveModuleAction (oldIndex, newIndex) {
  return (dispatch, getState) => {
    if (oldIndex < newIndex) {
      newIndex -= 1
    }

    const workflow = getState().workflow

    const newIds = workflow.wf_modules.slice()
    newIds.splice(newIndex, 0, ...newIds.splice(oldIndex, 1))
    // idToOrder: { '2': 1, '13': 2, '12': 0 }
    const idToOrder = newIds.map((id, order) => ({ id: Number(id), order }))

    return dispatch({
      type: MOVE_MODULE,
      payload: {
        promise: api.reorderWfModules(workflow.id, idToOrder),
        data: { newIds }
      }
    })
  }
}
registerReducerFunc(MOVE_MODULE + '_PENDING', (state, action) => {
  let { newIds } = action.payload
  return {
    ...state,
    workflow: {
      ...state.workflow,
      wf_modules: newIds
    }
  }
})

// ADD_MODULE
/**
 * Add a placeholder (phony String WfModule ID) to workflow.wf_modules and
 * send an API request to add the module; on completion, add to wfModules and
 * replace the placeholder in workflow.wf_modules with the new wfModule ID.
 *
 * Parameters:
 * @param moduleId String module id_name or Number module ID.
 * @param position Number or Object. If Number: position where this module
 *                 should be (i.e., position of the current module we will go
 *                 _before_). If Object, its `beforeWfModuleId` or
 *                 `afterWfModuleId` Number property will determine position.
 * @param parameterValues {id_name:value} Object of parameters for the
 *                        newly-created WfModule.
 */
export function addModuleAction (moduleId, position, parameterValues) {
  return (dispatch, getState) => {
    const { modules, workflow } = getState()
    if (typeof moduleId === 'string' || moduleId instanceof String) {
      moduleId = moduleIdNameToModuleId(modules, moduleId)
    }
    const nonce = generateNonce(moduleId)

    let index = position
    if (position.beforeWfModuleId) {
      const previous = workflow.wf_modules.indexOf(position.beforeWfModuleId)
      if (previous === -1) {
        console.warn("Ignoring addModuleAction with invalid position", position)
        return
      }
      index = previous
    }
    if (position.afterWfModuleId) {
      const previous = workflow.wf_modules.indexOf(position.afterWfModuleId)
      if (previous === -1) {
        console.warn("Ignoring addModuleAction with invalid position", position)
        return
      }
      index = previous + 1
    }

    return dispatch({
      type: ADD_MODULE,
      payload: {
        promise: (
          api.addModule(workflow.id, moduleId, index, parameterValues || {})
            .then(response => {
              return {
                nonce: nonce,
                data: response
              }
            })
        ),
        data: {
          nonce,
          index,
        }
      }
    })
  }
}

registerReducerFunc(ADD_MODULE + '_PENDING', (state, action) => {
  const wfModules = state.workflow.wf_modules.slice()

  let { index, nonce } = action.payload
  if (index === null) {
    index = wfModules.length
  }

  // Add a nonce to wf_modules Array of IDs. Don't add anything to wfModules:
  // users must assume that if it isn't in wfModules, it's a placeholder.
  wfModules.splice(index, 0, nonce)

  return { ...state,
    workflow: { ...state.workflow,
      wf_modules: wfModules
    }
  }
})
registerReducerFunc(ADD_MODULE + '_FULFILLED', (state, action) => {
  const { data, nonce } = action.payload
  const { wfModule, index } = data

  // Replace the nonce with the actual id
  const wfModuleIds = state.workflow.wf_modules
    .map(id => id === nonce ? wfModule.id : id)

  const wfModules = { ... state.wfModules,
    [String(data.wfModule.id)]: data.wfModule
  }

  return { ...state,
    workflow: { ...state.workflow,
      wf_modules: wfModuleIds
    },
    // Do _not_ overwrite the wfModule itself. We receive the wfModule over a
    // separate WebSockets message, so we don't know whether that message will
    // arrive before or after this one.
    selected_wf_module: index
  }
})

// DELETE_MODULE_ACTION
// Call delete API, then dispatch a reload
export function deleteModuleAction (wfModuleId) {
  return {
    type: DELETE_MODULE,
    payload: {
      promise: api.deleteModule(wfModuleId),
      data: { wfModuleId }
    }
  }
}
registerReducerFunc(DELETE_MODULE + '_PENDING', (state, action) => {
  const wfModuleId = action.payload.wfModuleId

  const wfModuleIds = state.workflow.wf_modules.slice()
  const index = wfModuleIds.indexOf(wfModuleId)
  if (index === -1) return state

  wfModuleIds.splice(index, 1)

  const wfModules = { ... state.wfModules }
  delete wfModules[String(wfModuleId)]

  // If we are deleting the selected module, then set the previous module
  // in stack as selected (behavior same as in models/Commands.py)
  let selected = state.selected_wf_module
  if (selected !== null && selected >= index) {
    selected -= 1
  }
  if (selected < 0) {
    selected = null
  }

  return { ...state,
    workflow: { ...state.workflow,
      wf_modules: wfModuleIds
    },
    wfModules,
    selected_wf_module: selected
  }
})

// SET_SELECTED_MODULE
// Set the selected module in the workflow
export function setSelectedWfModuleAction (index) {
  return (dispatch, getState) => {
    const workflow = getState().workflow

    // avoid spurious HTTP requests and state changes
    if (workflow.selected_wf_module === index) return

    // Fire-and-forget: tell the server about this new selected_wf_module,
    // so next time we load the page it will pass it in initState.
    api.setSelectedWfModule(workflow.id, index)
      .catch(console.warn)

    return dispatch({
      type: SET_SELECTED_MODULE,
      payload: index
    })
  }
}
registerReducerFunc(SET_SELECTED_MODULE, (state, action) => {
  return {
    ...state,
    selected_wf_module: action.payload
  }
})

// --- Workflow Module actions ---

/*
 * Tell the server to reload data from upstream.
 *
 * Only works if there is a 'version_select' custom parameter.
 */
export function maybeRequestWfModuleFetchAction (id) {
  return (dispatch, getState) => {
    const wfModule = getState().wfModules[String(id)]
    const hasVersionSelect = !!wfModule.parameter_vals.find(pv => pv.parameter_spec.id_name === 'version_select')

    if (!hasVersionSelect) return

    return dispatch({
      type: REQUEST_WF_MODULE_FETCH,
      payload: {
        promise: api.requestFetch(id)
          .then(() => ({ id }), (err) => { console.warn(err); return { id } }),
        data: { id }
      }
    })
  }
}

registerReducerFunc(REQUEST_WF_MODULE_FETCH + '_PENDING', (state, action) => {
  const { id } = action.payload
  const wfModule = state.wfModules[String(id)]

  // Set the WfModule to 'busy' on the client side.
  //
  // Don't conflict with the server side: use a client-specific variable.
  return { ...state,
    wfModules: { ...state.wfModules,
      [String(id)]: { ...wfModule,
        nClientRequests: (wfModule.nClientRequests || 0) + 1
      }
    }
  }
})

registerReducerFunc(REQUEST_WF_MODULE_FETCH + '_FULFILLED', (state, action) => {
  const { id } = action.payload
  const wfModule = state.wfModules[String(id)]

  if (!wfModule) return

  // Set the WfModule to 'busy' on the client side.
  //
  // A fetch might cause _all_ WfModules to become busy on the server, if it
  // kicks off a ChangeDataVersionCommand. If it doesn't, the other WfModules
  // will stay as they are. Let's not pre-emptively update those _other_
  // WfModule statuses, lest the server never tell us they won't change.
  return { ...state,
    wfModules: { ...state.wfModules,
      [String(id)]: { ...wfModule,
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
export function updateWfModuleAction (id, data) {
  return (dispatch, getState) => {
    const { wfModules } = getState()

    if (!wfModules[String(id)]) return Promise.resolve(null)

    return dispatch({
      type: UPDATE_WF_MODULE,
      payload: {
        promise: api.updateWfModule(id, data),
        data: {
          id,
          data
        }
      }
    })
  }
}
registerReducerFunc(UPDATE_WF_MODULE + '_PENDING', (state, action) => {
  const { id, data } = action.payload
  const wfModule = state.wfModules[String(id)]

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(id)]: { ...wfModule,
        ...data
      }
    }
  }
})

// SET_WF_MODULE_STATUS
// Change the workflow status (OK, pending, error)
export function setWfModuleStatusAction (wfModuleId, status, errorMsg) {
  return {
    type: SET_WF_MODULE_STATUS,
    payload: {
      wfModuleId,
      status: status,
      error_msg: errorMsg || ''
    }
  }
}
registerReducerFunc(SET_WF_MODULE_STATUS, (state, action) => {
  const { wfModuleId, status, error_msg } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule) return state

  if (wfModule.status === status && wfModule.error_msg === error_msg) {
    return state
  }

  return { ...state,
    wfModules: { ...state.wfModules,
      [String(wfModuleId)]: { ...wfModule,
        status,
        error_msg
      }
    }
  }
})

export function setWfModuleAction (wfModule) {
  return {
    type: SET_WF_MODULE,
    payload: { wfModule }
  }
}
registerReducerFunc(SET_WF_MODULE, (state, action) => {
  const { wfModule } = action.payload

  const id = String(wfModule.id)

  const existingWfModule = state.wfModules[id]
  if (!existingWfModule) {
    console.warn('Missing WfModule to replace:', wfModule)
    return state
  }

  return { ...state,
    wfModules: { ...state.wfModules,
      [id]: {
        ...existingWfModule,
        ...wfModule
      }
    }
  }
})

export function setWfModuleCollapsedAction (wfModuleId, isCollapsed, isReadOnly) {
  let promise
  if (isReadOnly) {
    promise = Promise.resolve(null)
  } else {
    promise = api.setWfModuleCollapsed(wfModuleId, isCollapsed)
  }

  return {
    type: SET_WF_MODULE_COLLAPSED,
    payload: {
      promise,
      data: {
        wfModuleId,
        isCollapsed
      }
    }
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
  return {
    type: SET_WF_MODULE_PARAMS,
    payload: {
      promise: api.setWfModuleParams(wfModuleId, params),
      data: {
        wfModuleId,
        params
      }
    }
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

// --- Parameter actions ---

// SET_PARAM_VALUE

// Internal API, requires all indices
function setParamValueActionBase (state, dispatch, wfModuleId, paramId, newValue) {
  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule) return Promise.resolve() // no module? Ignore

  const paramVal = wfModule.parameter_vals.find(v => v.id === paramId)
  if (!paramVal) return Promise.resolve() // no param? Ignore

  if (!newValue.hasOwnProperty('value')) {
    newValue = { value: newValue } // Cruft, hard to decipher why we do this
  }

  if (paramVal.value === newValue.value) return Promise.resolve(null) // no change? Ignore

  return dispatch({
    type: SET_PARAM_VALUE,
    payload: {
      promise: api.onParamChanged(paramId, newValue),
      data: {
        wfModuleId,
        paramId,
        paramValue: newValue.value
      }
    }
  })
}

// Most common form
export function setParamValueAction (paramId, paramValue) {
  return (dispatch, getState) => { // thunk
    const state = getState()
    for (const wfModuleIdString in state.wfModules) {
      const wfModule = state.wfModules[wfModuleIdString]
      for (const param of wfModule.parameter_vals) {
        if (param.id === paramId) {
          return setParamValueActionBase(state, dispatch, wfModule.id, paramId, paramValue)
        }
      }
    }

    return Promise.resolve() // no param? Do nothing
  }
}

// This action creator is used when we don't have a parameter id
export function setParamValueActionByIdName (wfModuleId, paramIdName, paramValue) {
  return (dispatch, getState) => { // thunk
    const state = getState()
    const wfModule = state.wfModules[String(wfModuleId)]
    if (!wfModule) return Promise.resolve() // no module? Do nothing

    for (const param of wfModule.parameter_vals) {
      if (param.parameter_spec && param.parameter_spec.id_name === paramIdName) {
        return setParamValueActionBase(state, dispatch, wfModule.id, param.id, paramValue)
      }
    }
  }
}

registerReducerFunc(SET_PARAM_VALUE + '_PENDING', (state, action) => {
  const { wfModuleId, paramId, paramValue } = action.payload
  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule) return state

  const paramVals = wfModule.parameter_vals.slice()
  const oldIndex = paramVals.findIndex(pv => pv.id === paramId)
  if (oldIndex === -1) return state

  paramVals[oldIndex] = { ...paramVals[oldIndex],
    value: paramValue
  }

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
  return {
    type: SET_DATA_VERSION,
    payload: {
      promise: api.setWfModuleVersion(wfModuleId, selectedVersion),
      data: {
        wfModuleId,
        selectedVersion
      }
    }
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
  let versionsToUpdate = [].concat(versions) // will accept one or many
  return {
    type: MARK_DATA_VERSIONS_READ,
    payload: {
      promise: api.markDataVersionsRead(wfModuleId, versionsToUpdate),
      data: {
        wfModuleId,
        versionsToUpdate
      }
    }
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
  return {
    type: CLEAR_NOTIFICATIONS,
    payload: {
      promise: api.deleteWfModuleNotifications(wfModuleId),
      data: {
        wfModuleId
      }
    }
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

export function mockStore (initialState) {
  // We don't bother with unit tests: we use more integration-test-y stuff. So
  // we test both the action generators and the state changes together.
  // (Rationale: it's rare for one to change without requiring a symmetric
  // change to the other.)
  return createStore(workflowReducer, initialState, applyMiddleware(...middlewares))
}
