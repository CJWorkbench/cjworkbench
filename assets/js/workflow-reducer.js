// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { getPageID } from './utils'

export const RELOAD_WORKFLOW = 'RELOAD_WORKFLOW';
export const CHANGE_PARAM = 'CHANGE_PARAM';

/*
export function changeParamAction(wfModule, paramID, newVal) {
  return { type: CHANGE_PARAM, wfModule: wfModule, newVal }
}
*/

// Load the whole workflow. Returns a promise which returns an action factory (function that returns an action)
// redux-promise
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

export function paramChangedAction(paramID, newVal) {
   return fetch('/api/parameters/' + paramID, {
      method: 'patch',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(newVal)
    })
    .then( reloadWorkflowAction );
}

const initialState = {};

// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion
export function workflowReducer(state = initialState, action) {
  switch (action.type) {

    case RELOAD_WORKFLOW:
      console.log("Reducing RELOAD_WORKFLOW action")
      console.log(action)
      return Object.assign({}, state, {
        workflow: action.workflow,
      })

    default:
      return state
  }
};
