// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { getPageID, csrfToken } from './utils'
import WorkbenchAPI from './WorkbenchAPI'
import { createStore, applyMiddleware } from 'redux'
import promiseMiddleware from 'redux-promise'

const CHANGE_PARAM = 'CHANGE_PARAM'
const RELOAD_WORKFLOW = 'RELOAD_WORKFLOW'
const INITIAL_LOAD_WORKFLOW = 'INITIAL_LOAD_WORKFLOW'
const REMOVE_MODULE_ACTION = 'REMOVE_MODULE'
const MODULE_STATUS_CHANGE = 'MODULE_STATUS_CHANGE'
const SELECTED_MODULE_CHANGE = 'SELECTED_MODULE_CHANGE'
const UPDATE_CURRENT_USER = 'UPDATE_CURRENT_USER'
const TOGGLE_MODULE_COLLAPSED = 'TOGGLE_MODULE_COLLAPSED'


var api = WorkbenchAPI(); // var so it can be mocked for testing

export function mockAPI(mock_api) {
  api = mock_api;
}

// ---- Our Store ----
// Master state for the workflow. Export so that components can store.dispatch()
// var so it can be mocked for testing
export var store = createStore(workflowReducer, window.initState, applyMiddleware(promiseMiddleware));

export function mockStore(mock_store) {
  store = mock_store;
}

// ---- Actions ----

// Load the whole workflow. Returns a promise which returns an action to dispatch when it completes
export function reloadWorkflowAction() {
  return (
    api.loadWorkflow(getPageID())
    .then(json => ({  type: RELOAD_WORKFLOW, workflow: json }))
  )
}

export function initialLoadWorkflowAction() {
  return (
    api.loadWorkflow(getPageID())
    .then(json => ({ type: INITIAL_LOAD_WORKFLOW, workflow: json }))
  )
}

// Make an addModule call, then reload the workflow
export function addModuleAction(moduleId, insertBefore) {
  return (
    api.addModule(getPageID(), moduleId, insertBefore)
    .then( data => store.dispatch(changeSelectedWfModuleAction(data.id)))
    .then( reloadWorkflowAction )
  )
}

// Call delete API, then dispatch a reload
export function removeModuleAction(id_to_delete) {

  // If we are deleting the selected module, then set previous module in stack as selected
  var state = store.getState();
  if (id_to_delete === state.selected_wf_module) {

    // Find id of previous in stack
    var wf_modules = state.workflow.wf_modules;
    var new_selected_id = null;
    for (var wfm of wf_modules) {
      if (wfm.id === id_to_delete)
        break;
      new_selected_id = wfm.id;
    }

    // if we are deleting first module, set to new first module if any
    if (new_selected_id === null) {
      if (wf_modules.length > 1)
        new_selected_id = wf_modules[1].id;
      else
        new_selected_id = null;
    }

    store.dispatch(changeSelectedWfModuleAction(new_selected_id))
  }

  return (
    api.deleteModule(id_to_delete)
    .then( reloadWorkflowAction )
  )
}

export function wfModuleStatusAction(wfModuleID, status, error_msg='') {
  return {
    type : MODULE_STATUS_CHANGE,
    id : wfModuleID,
    status : status,
    error_msg: error_msg
  }
}

export function changeSelectedWfModuleAction(wfModuleID) {
  return {
    type : SELECTED_MODULE_CHANGE,
    id : wfModuleID,
  }
}

export function toggleModuleCollapsedAction(wfModuleID, isCollapsed) {
  return {
    type : TOGGLE_MODULE_COLLAPSED,
    id : wfModuleID,
    isCollapsed
  }
}

export function updateCurrentUserAction() {
  return (
    api.currentUser()
      .then(user => ({type : UPDATE_CURRENT_USER, user: user}))
  )
}

export function disconnectCurrentUserAction(credentialId) {
  return (
    api.disconnectCurrentUser( credentialId )
      .then( updateCurrentUserAction )
  )
}

export function updateWfModuleAction(id, data) {
  return (
    api.updateWfModule(id, data)
      // TODO: Eventually this should return a workflow that replaces the old
      // one in the global store but for now just reload
      .then( reloadWorkflowAction )
  )
}

export function clearNotificationsAction(id) {
  return (
    api.deleteWfModuleNotifications(id)
      .then( reloadWorkflowAction )
  )
}

// ---- Reducer ----
// Maps actions to state changes, for that is the Redux way
// Our state fields:
//
//  workflow            - the current workflow as returned from /api/workflows/n
//  selected_wf_module  - id of selected (usually last-clicked) module, drives output pane

// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion

export function workflowReducer(state, action) {
  if (!state) {
    state = {}; // initial state. we'll load a workflow soon.
  }

  switch (action.type) {

    // Reload entire state
    case RELOAD_WORKFLOW:
      console.log("RELOAD_WORKFLOW");
      console.log("new workflow revision " + action.workflow.revision);
      return Object.assign({}, state, {
        workflow: action.workflow
      });

    // Sets the selected module to the first in list
    case INITIAL_LOAD_WORKFLOW:
      console.log("INITIAL_LOAD_WORKFLOW");
      if (action.workflow.wf_modules && action.workflow.wf_modules.length) {
        return Object.assign({}, state, {
          selected_wf_module: action.workflow.wf_modules[0].id,
          workflow: action.workflow
        });
      } else {
        return Object.assign({}, state, {
          workflow: action.workflow
        });
      }

    // Change id of module currently selected
    case SELECTED_MODULE_CHANGE:
      // console.log(SELECTED_MODULE_CHANGE + " old " +  state.selected_wf_module + " new " + action.id);
      if (!'selected_wf_module' in state || (action.id != state.selected_wf_module)) {
        return Object.assign({}, state, {
          selected_wf_module: action.id,
        });
      } else {
        return state;
      }

    // Change status on a single module
    case MODULE_STATUS_CHANGE:
      //console.log(WF_MODULE_STATUS_CHANGE + " " + action.id);
      if ('wf_modules' in state.workflow) {

        var newState = state;

        for (var wfm of newState.workflow.wf_modules) {

          // Find matching module, and change state if status changed or error message changed
          if (wfm.id == action.id &&
              ((wfm.status != action.status) || (wfm.status=='error' && wfm.error_msg != action.error_msg))) {
            // console.log("actually changed status for " + wfm.id);

            // Create a copy of the wf_module with new status
            var newWfm = Object.assign({}, wfm, { status: action.status, error_msg: action.error_msg });

            // Clone the state, switch out this one wfm (keep position in wf_modules array )
            newState = Object.assign({}, state);
            newState.workflow = Object.assign({}, state.workflow);
            newState.workflow.wf_modules = state.workflow.wf_modules.map(el => el!==wfm ? el : newWfm);
          }
        }
        return newState;
      } else {
        return state;
      }

    case TOGGLE_MODULE_COLLAPSED:
      //console.log(WF_MODULE_STATUS_CHANGE + " " + action.id);
      if ('wf_modules' in state.workflow) {

        var newState = state;

        console.log(action);

        for (var wfm of newState.workflow.wf_modules) {

          // Find matching module, and change state if status changed or error message changed
          if (wfm.id == action.id) {
            // Create a copy of the wf_module with new status
            console.log('heeeey');
            var newWfm = Object.assign({}, wfm, {
              is_collapsed: action.isCollapsed
            });

            // Clone the state, switch out this one wfm (keep position in wf_modules array )
            newState = Object.assign({}, state);
            newState.workflow = Object.assign({}, state.workflow);
            newState.workflow.wf_modules = state.workflow.wf_modules.map(el => el!==wfm ? el : newWfm);
          }
        }
        return newState;
      } else {
        return state;
      }

    case UPDATE_CURRENT_USER:
      if (state.user !== action.user) {
        return Object.assign({}, state, {
          user: action.user,
        });
      } else {
        return state;
      }

    default:
      return state
  }
}
