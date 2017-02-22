// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { getPageID } from './utils'
import { createStore, applyMiddleware } from 'redux'
import promiseMiddleware from 'redux-promise';

export const RELOAD_WORKFLOW = 'RELOAD_WORKFLOW';
export const CHANGE_PARAM = 'CHANGE_PARAM';
export const WF_MODULE_STATUS_CHANGE = 'WF_MODULE_STATUS_CHANGE';

// ---- Our Store ----
// Master state for the workflow. Export so that components can store.dispatch()

export let store = createStore(workflowReducer, applyMiddleware(promiseMiddleware));

// ---- Actions ----

// Load the whole workflow. Returns a promise which returns an action to dispatch when it completes
export function reloadWorkflowAction() {
  return fetch('/api/workflows/' + getPageID())
    .then(response => response.json())
    .then(json => ({  type: RELOAD_WORKFLOW, workflow: json }));
}

// Make an addModule call, then reload the workflow
export function addModuleAction(newModuleID) {
  return fetch('/api/workflows/' + getPageID() + "/addmodule", {
    method: 'put',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({insertBefore: 0, moduleID: newModuleID})
  }) .then( reloadWorkflowAction );
}

export function wfModuleStatusAction(wfModuleID, status, error_msg='') {
  return {
    type : WF_MODULE_STATUS_CHANGE,
    id : wfModuleID,
    status : status,
    error_msg: error_msg
  }
}

// ---- Reducer ----
// Maps actions to state changes, for that is the Redux way

// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion
export function workflowReducer(state, action) {
  if (!state) {
    state = {}; // initial state. we'll load a workflow soon.
  }

  switch (action.type) {

    // Reload entire state
    case RELOAD_WORKFLOW:
      console.log("RELOAD_WORKFLOW");
      return Object.assign({}, state, {
        workflow: action.workflow,
      })

    // Change status on a single module
    case WF_MODULE_STATUS_CHANGE:
      console.log(WF_MODULE_STATUS_CHANGE);
      if ('wf_modules' in state.workflow) {

        var newState = state;

        for (var wfm of newState.workflow.wf_modules) {
          if (wfm.id == action.id && wfm.status != action.status) {
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
};
