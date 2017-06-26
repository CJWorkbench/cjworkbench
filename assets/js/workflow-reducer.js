// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { getPageID, csrfToken } from './utils'
import { createStore, applyMiddleware } from 'redux'
import promiseMiddleware from 'redux-promise'

const CHANGE_PARAM = 'CHANGE_PARAM'
const RELOAD_WORKFLOW = 'RELOAD_WORKFLOW'
const REMOVE_MODULE_ACTION = 'REMOVE_MODULE'
const MODULE_STATUS_CHANGE = 'MODULE_STATUS_CHANGE'
const SELECTED_MODULE_CHANGE = 'SELECTED_MODULE_CHANGE'

// ---- Our Store ----
// Master state for the workflow. Export so that components can store.dispatch()

export let store = createStore(workflowReducer, applyMiddleware(promiseMiddleware));

// ---- Actions ----

// Load the whole workflow. Returns a promise which returns an action to dispatch when it completes
export function reloadWorkflowAction() {
  return fetch('/api/workflows/' + getPageID(), { credentials: 'include'})
    .then(response => response.json())
    .then(json => ({  type: RELOAD_WORKFLOW, workflow: json }));
}

// Make an addModule call, then reload the workflow
export function addModuleAction(module_id, insertBefore) {
  return fetch('/api/workflows/' + getPageID() + "/addmodule", {
    method: 'put',
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({insertBefore: insertBefore, moduleID: module_id})
  }) .then( reloadWorkflowAction );
}

// Call delete API, then dispatch a reload
export function removeModuleAction(wf_module_id) {

  //console.log("Deleting module " + wf_module_id);
  //console.log("Selected module " + store.getState().selected_module);

  // If we are deleting the selected module, then no selected module
  if (wf_module_id == store.getState().selected_wf_module) {
    console.log("Deleting selected module");
    store.dispatch(changeSelectedWfModuleAction(null))
  }

  return fetch('/api/wfmodules/' + wf_module_id, {
    method: 'delete',
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken
    },
  }).then( reloadWorkflowAction );
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

    default:
      return state
  }
}


