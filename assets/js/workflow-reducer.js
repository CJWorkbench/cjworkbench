// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { generateSlug } from './utils'
import applyUpdate from './reducers/applyUpdate'
import { reducerFunctions as ReportReducerFunctions } from './WorkflowEditor/Report/actions'
import { reducerFunctions as StepListReducerFunctions } from './WorkflowEditor/StepList/actions'
import { reducerFunctions as TabReducerFunctions } from './WorkflowEditor/Tabs/actions'
import { reducerFunctions as WorkflowEditorReducerFunctions } from './WorkflowEditor/actions'
import { reducerFunctions as ShareReducerFunctions } from './ShareModal/actions'
import { reducerFunctions as FileReducerFunctions } from './params/File/actions'
import selectIsReadOnly from './selectors/selectIsReadOnly'

// Workflow
const SET_WORKFLOW_NAME = 'SET_WORKFLOW_NAME'
const SET_SELECTED_MODULE = 'SET_SELECTED_MODULE'

// Delta: workflow+step changes
const APPLY_DELTA = 'APPLY_DELTA'

// Module: changes to Workbench modules
const UPDATE_MODULE = 'UPDATE_MODULE'

// Step
const ADD_STEP = 'ADD_STEP'
const DELETE_STEP = 'DELETE_STEP'
const MOVE_STEP = 'MOVE_STEP'
const SET_STEP_NOTES = 'SET_STEP_NOTES'
const SET_STEP_COLLAPSED = 'SET_STEP_COLLAPSED'
const REQUEST_STEP_FETCH = 'REQUEST_STEP_FETCH'
const SET_STEP_PARAMS = 'SET_STEP_PARAMS'
const SET_STEP_NOTIFICATIONS = 'SET_STEP_NOTIFICATIONS'
const SET_STEP_SECRET = 'SET_STEP_SECRET'

// Data versions/notifications
const SET_DATA_VERSION = 'SET_DATA_VERSION'

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
  console.warn(
    'Unhandled error during %s dispatch',
    action.type,
    action.payload
  )

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
  ...ReportReducerFunctions,
  ...ShareReducerFunctions,
  ...StepListReducerFunctions,
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

// 'data' is { mutationId, updateWorkflow, updateSteps, updateTabs, clearTabSlugs, clearStepIds }, all
// optional
export function applyDeltaAction (data) {
  return { type: APPLY_DELTA, payload: data }
}
registerReducerFunc(APPLY_DELTA, (state, action) => {
  return applyUpdate(state, action.payload)
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

// MOVE_STEP
// Re-order the modules in the step list
export function moveStepAction (tabSlug, oldIndex, newIndex) {
  return (dispatch, getState, api) => {
    if (oldIndex < newIndex) {
      newIndex -= 1
    }

    const { tabs } = getState()
    const tab = tabs[tabSlug]

    const newIds = tab.step_ids.slice()
    newIds.splice(newIndex, 0, ...newIds.splice(oldIndex, 1))

    return dispatch({
      type: MOVE_STEP,
      payload: {
        promise: api.reorderSteps(tabSlug, newIds),
        data: {
          tabSlug,
          stepIds: newIds
        }
      }
    })
  }
}
registerReducerFunc(MOVE_STEP + '_PENDING', (state, action) => {
  const { tabSlug, stepIds } = action.payload
  const tab = state.tabs[tabSlug]

  const oldIndex = tab.selected_step_position
  const oldId = tab.step_ids[oldIndex]
  const newIndex = stepIds.indexOf(oldId)

  return {
    ...state,
    tabs: {
      ...state.tabs,
      [tabSlug]: {
        ...tab,
        step_ids: stepIds,
        selected_step_position: newIndex
      }
    }
  }
})

// ADD_STEP
/**
 * Add a placeholder (phony String Step ID) to tab.step_ids and
 * send an API request to add the step; on completion, add to steps and
 * replace the placeholder in tab.step_ids with the new step ID.
 *
 * Parameters:
 * @param moduleId String module id_name or Number module ID.
 * @param position Object position this module should be in. One of:
 *                 * { tabSlug, index }
 *                 * { beforeStepId }
 *                 * { afterStepId }
 * @param parameterValues {idName:value} Object of parameters for the
 *                        newly-created Step.
 */
export function addStepAction (moduleIdName, position, parameterValues) {
  return (dispatch, getState, api) => {
    const { tabs, steps } = getState()
    const nonce = generateNonce(steps, moduleIdName)
    const slug = generateSlug('step-')

    let tabSlug, index

    if (position.tabSlug !== undefined && position.index !== undefined) {
      tabSlug = position.tabSlug
      index = position.index
    } else {
      const aStepId = position.beforeStepId || position.afterStepId
      const aStep = steps[String(aStepId)]
      tabSlug = aStep.tab_slug
      const tab = tabs[tabSlug]

      if (position.beforeStepId) {
        const previous = tab.step_ids.indexOf(position.beforeStepId)
        if (previous === -1) {
          console.warn('Ignoring addStepAction with invalid position', position)
          return
        }
        index = previous
      }
      if (position.afterStepId) {
        const previous = tab.step_ids.indexOf(position.afterStepId)
        if (previous === -1) {
          console.warn('Ignoring addStepAction with invalid position', position)
          return
        }
        index = previous + 1
      }
    }

    return dispatch({
      type: ADD_STEP,
      payload: {
        promise: api
          .addStep(tabSlug, slug, moduleIdName, index, parameterValues || {})
          .then(response => {
            return {
              tabSlug,
              slug,
              nonce: nonce,
              data: response
            }
          }),
        data: {
          tabSlug,
          slug,
          index,
          nonce
        }
      }
    })
  }
}

registerReducerFunc(ADD_STEP + '_PENDING', (state, action) => {
  const { tabs } = state
  const { tabSlug, index, nonce } = action.payload
  const tab = tabs[tabSlug]
  const stepIds = tab.step_ids.slice()

  // Add a nonce to steps Array of IDs. Don't add anything to steps:
  // users must assume that if it isn't in steps, it's a placeholder.
  stepIds.splice(index, 0, nonce)

  return {
    ...state,
    tabs: {
      ...tabs,
      [tabSlug]: {
        ...tab,
        step_ids: stepIds,
        selected_step_position: index
      }
    }
  }
})

// DELETE_STEP
// Call delete API, then dispatch a reload
export function deleteStepAction (stepId) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: DELETE_STEP,
      payload: {
        promise: api.deleteStep(stepId),
        data: { stepId }
      }
    })
  }
}
registerReducerFunc(DELETE_STEP + '_PENDING', (state, action) => {
  const { stepId } = action.payload

  const { tabs, steps } = state
  const step = steps[String(stepId)]
  const tab = tabs[step.tab_slug]

  const stepIds = tab.step_ids.slice()
  const index = stepIds.indexOf(stepId)
  if (index === -1) return state

  stepIds.splice(index, 1)

  const newSteps = { ...state.steps }
  delete newSteps[String(stepId)]

  // If we are deleting the selected module, then set the previous module
  // in stack as selected
  let selected = tab.selected_step_position
  if (selected !== null && selected >= index) {
    selected -= 1
  }
  if (selected < 0) {
    selected = 0
  }
  if (!Object.keys(newSteps).length) {
    selected = null
  }

  return {
    ...state,
    tabs: {
      ...tabs,
      [tab.slug]: {
        ...tab,
        step_ids: stepIds,
        selected_step_position: selected
      }
    },
    steps: newSteps
  }
})

// SET_SELECTED_MODULE
// Set the selected module in the workflow
export function setSelectedStepAction (stepId) {
  return (dispatch, getState, api) => {
    const state = getState()
    const { workflow, tabs, steps } = state

    const step = steps[String(stepId)]
    if (!step) return

    const tabSlug = step.tab_slug
    const tab = tabs[tabSlug]

    const tabPosition = workflow.tab_slugs.indexOf(tabSlug)
    const stepPosition = tab.step_ids.indexOf(stepId)

    if (
      workflow.selected_tab_position === tabPosition &&
      tab.selected_step_position === stepPosition
    ) {
      // avoid spurious HTTP requests and state changes
      return
    }

    // Fire-and-forget: tell the server about this new selection
    // so next time we load the page it will pass it in initState.
    const promise = selectIsReadOnly(state)
      ? Promise.resolve(null)
      : api.setSelectedStep(stepId)
    return dispatch({
      type: SET_SELECTED_MODULE,
      payload: {
        promise,
        data: { tabPosition, tabSlug, stepPosition }
      }
    })
  }
}
registerReducerFunc(SET_SELECTED_MODULE + '_PENDING', (state, action) => {
  const { workflow, tabs } = state
  const { tabPosition, tabSlug, stepPosition } = action.payload
  const tab = tabs[tabSlug]

  return {
    ...state,
    selectedPane: {
      // so we navigate to the Step
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
        selected_step_position: stepPosition
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
export function maybeRequestStepFetchAction (stepId) {
  return (dispatch, getState, api) => {
    const { steps, modules } = getState()
    const step = steps[String(stepId)]
    const module = step.module ? modules[step.module] : null
    const hasVersionSelect = module
      ? !!module.param_fields.find(ps => ps.idName === 'version_select')
      : null

    if (!hasVersionSelect) return

    return dispatch({
      type: REQUEST_STEP_FETCH,
      payload: {
        promise: api.requestFetch(stepId).then(
          () => ({ stepId }),
          err => {
            console.warn(err)
            return { stepId }
          }
        ),
        data: { stepId }
      }
    })
  }
}

registerReducerFunc(REQUEST_STEP_FETCH + '_PENDING', (state, action) => {
  const { stepId } = action.payload
  const step = state.steps[String(stepId)]

  // Set the Step to 'busy' on the client side.
  //
  // Don't conflict with the server side: use a client-specific variable.
  return {
    ...state,
    steps: {
      ...state.steps,
      [String(stepId)]: {
        ...step,
        nClientRequests: (step.nClientRequests || 0) + 1
      }
    }
  }
})

registerReducerFunc(REQUEST_STEP_FETCH + '_FULFILLED', (state, action) => {
  const { stepId } = action.payload
  const step = state.steps[String(stepId)]

  if (!step) return

  // Set the Step to 'busy' on the client side.
  //
  // A fetch might cause _all_ Steps to become busy on the server, if it
  // kicks off a SetStepDataVersion command. If it doesn't, the other Steps
  // will stay as they are. Let's not pre-emptively update those _other_
  // Step statuses, lest the server never tell us they won't change.
  return {
    ...state,
    steps: {
      ...state.steps,
      [String(stepId)]: {
        ...step,
        nClientRequests: (step.nClientRequests || 1) - 1
      }
    }
  }
})

/**
 * Set whether a Step emails the workflow owner on update.
 */
export function setStepNotificationsAction (stepId, isNotifications) {
  return (dispatch, getState, api) => {
    const { steps } = getState()
    if (!steps[String(stepId)]) return Promise.resolve(null)

    return dispatch({
      type: SET_STEP_NOTIFICATIONS,
      payload: {
        promise: api.setStepNotifications(stepId, isNotifications),
        data: {
          stepId,
          isNotifications
        }
      }
    })
  }
}
registerReducerFunc(SET_STEP_NOTIFICATIONS + '_PENDING', (state, action) => {
  const { stepId, isNotifications } = action.payload
  const step = state.steps[String(stepId)]
  return {
    ...state,
    steps: {
      ...state.steps,
      [String(stepId)]: {
        ...step,
        notifications: isNotifications
      }
    }
  }
})

export function setStepNotesAction (stepId, notes) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: SET_STEP_NOTES,
      payload: {
        promise: api.setStepNotes(stepId, notes),
        data: { stepId, notes }
      }
    })
  }
}
registerReducerFunc(SET_STEP_NOTES + '_PENDING', (state, action) => {
  const { stepId, notes } = action.payload
  const step = state.steps[String(stepId)]
  if (step) {
    return {
      ...state,
      steps: {
        ...state.steps,
        [String(stepId)]: {
          ...step,
          notes
        }
      }
    }
  } else {
    return state
  }
})

export function setStepCollapsedAction (stepId, isCollapsed) {
  return (dispatch, getState, api) => {
    let promise
    if (selectIsReadOnly(getState())) {
      promise = Promise.resolve(null)
    } else {
      promise = api.setStepCollapsed(stepId, isCollapsed)
    }

    return dispatch({
      type: SET_STEP_COLLAPSED,
      payload: {
        promise,
        data: {
          stepId,
          isCollapsed
        }
      }
    })
  }
}
registerReducerFunc(SET_STEP_COLLAPSED + '_PENDING', (state, action) => {
  const { stepId, isCollapsed } = action.payload
  const step = state.steps[stepId]
  if (!step) return state

  return {
    ...state,
    steps: {
      ...state.steps,
      [String(stepId)]: {
        ...step,
        is_collapsed: isCollapsed
      }
    }
  }
})

export function setStepParamsAction (stepId, params) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: SET_STEP_PARAMS,
      payload: {
        promise: api.setStepParams(stepId, params),
        data: {
          stepId,
          params
        }
      }
    })
  }
}

registerReducerFunc(SET_STEP_PARAMS + '_PENDING', (state, action) => {
  const { stepId, params } = action.payload
  const step = state.steps[String(stepId)]

  return {
    ...state,
    steps: {
      ...state.steps,
      [String(stepId)]: {
        ...step,
        params: {
          ...step.params,
          ...params
        }
      }
    }
  }
})

export function setStepSecretAction (stepId, param, secret) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: SET_STEP_SECRET,
      payload: {
        promise: api.setSecret(stepId, param, secret),
        data: {
          stepId,
          param
        }
      }
    })
  }
}

// --- Data Version actions ---

// SET_DATA_VERSION
export function setDataVersionAction (stepId, selectedVersion) {
  return (dispatch, getState, api) => {
    return dispatch({
      type: SET_DATA_VERSION,
      payload: {
        promise: api.setStepVersion(stepId, selectedVersion),
        data: {
          stepId,
          selectedVersion
        }
      }
    })
  }
}
registerReducerFunc(SET_DATA_VERSION + '_PENDING', (state, action) => {
  const { stepId, selectedVersion } = action.payload
  const step = state.steps[String(stepId)]
  if (!step) return state

  return {
    ...state,
    steps: {
      ...state.steps,
      [String(stepId)]: {
        ...step,
        versions: {
          ...step.versions,
          selected: selectedVersion
        }
      }
    }
  }
})

export function startCreateSecretAction (stepId, param) {
  return (dispatch, getState, api) => {
    api.startCreateSecret(stepId, param)
  }
}

export function deleteSecretAction (stepId, param) {
  return (dispatch, getState, api) => {
    // TODO consider modifying state. Right now we don't. When the user clicks
    // "sign out", we only show feedback after the server has deleted the param
    // and sent a delta. Maybe that's actually what we want?.... Or maybe we
    // need immediate feedback in
    // the state.
    api.deleteSecret(stepId, param)
  }
}

function quickFixPrependStep (stepId, { moduleSlug, partialParams }) {
  return addStepAction(moduleSlug, { beforeStepId: stepId }, partialParams)
}

export function quickFixAction (stepId, action) {
  return {
    prependStep: quickFixPrependStep
  }[action.type](stepId, action)
}

// ---- Reducer ----
// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion

export function workflowReducer (state = {}, action) {
  if (action.error === true) {
    return handleError(state, action)
  }

  if (action.type in reducerFunc) {
    // Run a registered reducer
    return reducerFunc[action.type](state, action)
  }

  return state
}
