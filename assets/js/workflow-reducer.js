// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { nonce } from './utils'
import WorkbenchAPI from './WorkbenchAPI'
import { createStore, applyMiddleware, compose } from 'redux'
import promiseMiddleware from 'redux-promise-middleware'
import thunk from 'redux-thunk'
import { newContext } from 'immutability-helper'
import { validLessonHighlight } from './util/LessonHighlight'

// Workflow
const INITIAL_LOAD_WORKFLOW = 'INITIAL_LOAD_WORKFLOW';
const RELOAD_WORKFLOW = 'RELOAD_WORKFLOW';
const LOAD_MODULES = 'LOAD_MODULES'
const ADD_MODULE = 'ADD_MODULE';
const DELETE_MODULE = 'DELETE_MODULE';
const SET_SELECTED_MODULE = 'SET_SELECTED_MODULE';
const SET_WORKFLOW_PUBLIC = 'SET_WORKFLOW_PUBLIC';
const SET_WF_LIBRARY_COLLAPSE = 'SET_WF_LIBRARY_COLLAPSE';
const MOVE_MODULE = 'MOVE_MODULE';
const SET_LESSON_HIGHLIGHT = 'SET_LESSON_HIGHLIGHT';

// WfModule
const SET_WF_MODULE_STATUS = 'SET_WF_MODULE_STATUS';
const SET_WF_MODULE_COLLAPSED = 'SET_WF_MODULE_COLLAPSED';
const UPDATE_WF_MODULE = 'UPDATE_WF_MODULE';

// Parameter
const SET_PARAM_VALUE = 'SET_PARAM_VALUE';

// Data versions/notifications
const GET_DATA_VERSIONS = 'GET_DATA_VERSIONS';
const SET_DATA_VERSION = 'SET_DATA_VERSION';
const MARK_DATA_VERSIONS_READ = 'MARK_DATA_VERSIONS_READ';
const CLEAR_NOTIFICATIONS = 'CLEAR_NOTIFICATIONS';

// Sometimes, do nothing
export const NOP_ACTION = 'NOP_ACTION';
const NOP = { type: NOP_ACTION, payload: {} }

const WorkflowId = window.initState ? window.initState.workflowId : 'MISSING-WORKFLOW-ID';

var api = WorkbenchAPI(); // var so it can be mocked for testing

export function mockAPI(mock_api) {
  api = mock_api;
}

// ---- Our Store ----
// Master state for the workflow. Export so that components can store.dispatch()
// var so it can be mocked for testing
const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose
export var store = createStore( // TODO make it const
  workflowReducer,
  window.initState,
  composeEnhancers(applyMiddleware(promiseMiddleware(), thunk))
);

export function mockStore(mock_store) {
  store = mock_store;
}

const reducerFunc = {};

const registerReducerFunc = (key, func) => {
  reducerFunc[key] = func;
};

const nonces = [];
const generateNonce = (prefix) => {
  // Generate a nonce with some prefix from
  // the object we're creating the nonce for
  let returnNonce = nonce(prefix);
  // If it's not in the list,
  if (nonces.indexOf(returnNonce) === -1) {
    // Add it (since we know it's unique)
    nonces.push(returnNonce);
    // And return it
    return returnNonce;
  // Otherwise,
  } else {
    // try again
    return generateNonce(prefix);
  }
};
const removeNonce = (nonce) => {
  let nonceIndex = nonces.indexOf(nonce);
  if (nonceIndex !== -1) {
    nonces.splice(nonceIndex, 1);
  }
};

const update = newContext();
update.extend('$reorder', function(value, original) {
  let oldIndex, newIndex;
  [oldIndex, newIndex] = value;
  let newArray = original.slice();
  newArray.splice(newIndex, 0, newArray.splice(oldIndex, 1)[0]);
  return newArray;
});

// ---- Utilities for translating between ID and index ----

export function findIdxByProp(searchArray, searchProp, searchValue) {
  let returnIdx;
  for (let i = 0; i < searchArray.length; i++) {
    if (searchArray[i][searchProp] === searchValue) {
      returnIdx = i;
      break;
    }
  }
  return returnIdx;
}

export function findParamIdxByIdName(wf_module, paramIdName) {
  let paramIdx;
  let len = wf_module.parameter_vals.length;
  for(let i = 0; i < len; i++) {
    if (wf_module.parameter_vals[i].parameter_spec.id_name === paramIdName) {
      paramIdx = i;
      break;
    }
  }
  if (paramIdx === len)
    return undefined;  // not found
  return paramIdx;
}

// find module that contains parameter
export function paramIdToIndices(workflow, paramId) {

  let modules = workflow.wf_modules;
  for(let wfModuleIdx = 0; wfModuleIdx < modules.length; wfModuleIdx ++) {

    let params = modules[wfModuleIdx ].parameter_vals;
    for(let paramIdx = 0; paramIdx < params.length; paramIdx++) {

      if (params[paramIdx].id === paramId) {
        return {
          wfModuleIdx,
          paramIdx
        }
      }
    }
  }

  return {
    wfModuleIdx : undefined,
    paramIdx : undefined
  }
}

// ---- Actions ----

// -- Workflow actions --


// INITIAL_LOAD_WORKFLOW
// Load the workflow for the first time
export function initialLoadWorkflowAction() {
  return {
    type: INITIAL_LOAD_WORKFLOW,
    payload: api.loadWorkflow(WorkflowId),
  }
}
registerReducerFunc(INITIAL_LOAD_WORKFLOW + '_FULFILLED', (state, action) => {
  // Sets the selected module from backend if it exists, or the first module if there are any at all
  let selectedWfModule = null;

  if (action.payload.selected_wf_module) {
    selectedWfModule = action.payload.selected_wf_module;
  } else if (action.payload.wf_modules && action.payload.wf_modules.length) {
    selectedWfModule = action.payload.wf_modules[0].id;
  }

  return Object.assign({}, state, {
    selected_wf_module: selectedWfModule,
    workflow: action.payload
  });
});

// RELOAD_WORKFLOW
// Re-load the workflow
// TODO: Do we need both initial and reload?
export function reloadWorkflowAction() {
  return {
    type: RELOAD_WORKFLOW,
    payload: api.loadWorkflow(WorkflowId).then((json) => {return json})
  }
}
registerReducerFunc(RELOAD_WORKFLOW + '_FULFILLED', (state, action) => {
  return update(state, {
    workflow: {$merge: action.payload},
    selected_wf_module: {$set: action.payload.selected_wf_module},
  });
});

// LOAD_MODULES
// Populate/refresh the module library
export function loadModulesAction() {
  return {
    type: LOAD_MODULES,
    payload: api.getModules()
  }
}
registerReducerFunc(LOAD_MODULES + '_FULFILLED', (state, action) => {
  return update(state, {
    modules: {$set: action.payload}
  });
});

// SET_WORKFLOW_PUBLIC
// Set the workflow to public or private
export function setWorkflowPublicAction(workflowId, isPublic) {
  return function (dispatch) {
    return (

      dispatch({
        type: SET_WORKFLOW_PUBLIC,
        payload: api.setWorkflowPublic(workflowId, isPublic)
      }).then( () => {

      dispatch(
        reloadWorkflowAction()
      )

    }));

  }
}

// MOVE_MODULE
// Re-order the modules in the module stack
export function moveModuleAction(oldIndex, newIndex) {
  if (oldIndex < newIndex) {
    newIndex -= 1;
  }
  // todo avoid store.getState() here:
  let newState = update(store.getState(), {
    workflow: {
      wf_modules: { $reorder: [ oldIndex, newIndex ] }
    }
  });
  let newOrder = newState.workflow.wf_modules.map( (item, i) => {return { id: item.id, order: i } } );

  return {
    type: MOVE_MODULE,
    payload: {
      promise: api.reorderWfModules(WorkflowId, newOrder),
      data: { oldIndex, newIndex },
    }
  }
}
registerReducerFunc(MOVE_MODULE + '_PENDING', (state, action) => {
  let { oldIndex, newIndex } = action.payload
  if (oldIndex < newIndex) {
    newIndex -= 1;
  }
  return update(state, {
    workflow: {
      wf_modules: { $reorder: [ oldIndex, newIndex ] }
    }
  });
});

// ADD_MODULE
export function addModuleAction(moduleId, insertBefore, placeholder) {
  let nonce = generateNonce(moduleId);

  let payload = {
    promise: api.addModule(WorkflowId, moduleId, insertBefore)
      .then((response) => {
        response.pendingId = nonce;
        return response;
      }),
  };

  if (typeof placeholder !== 'undefined') {
    payload.data = placeholder;
  } else {
    payload.data = {}
  }

  payload.data.placeholder = true;
  payload.data.insert_before = insertBefore;
  payload.data.pendingId = nonce;

  return {
      type: ADD_MODULE,
      payload: payload
    }
}

registerReducerFunc(ADD_MODULE + '_PENDING', (state, action) => {
  let insertBefore = action.payload.insert_before;

  if (insertBefore === null) {
    insertBefore = state.workflow.wf_modules.length - 1;
  }

  delete action.payload.insert_before;

  return update(state, {
    workflow: {
      wf_modules: { $splice:[ [insertBefore, 0, action.payload] ] }
    }
  });
});
registerReducerFunc(ADD_MODULE + '_FULFILLED', (state, action) => {
  let insertBefore,
      overwrite = 1;

  if (typeof action.payload.pendingId === 'undefined') {
    // There's no placeholder. Maybe one of our collaborators added this module
    // on a different client
    overwrite = 0;
    insertBefore = action.payload.insert_before;
  } else {
    insertBefore = findIdxByProp(state.workflow.wf_modules, 'pendingId', action.payload.pendingId);
    removeNonce(action.payload.pendingId);
  }

  delete action.payload.insert_before;

  return update(state, {
    selected_wf_module: {$set: action.payload.id},  // set selected to just-added module
    workflow: {
      wf_modules: { $splice:[ [insertBefore, overwrite, action.payload] ] }
    }
  });
});


// DELETE_MODULE_ACTION
// Call delete API, then dispatch a reload
export function deleteModuleAction(id_to_delete) {
  return {
    type: DELETE_MODULE,
    payload: {
      promise: api.deleteModule(id_to_delete),
      data: {
        wf_module_id: id_to_delete
      }
    }
  }
}
registerReducerFunc(DELETE_MODULE + '_PENDING', (state, action) => {
  const wfModuleId = action.payload.wf_module_id;
  const wfModuleIdx = state.workflow.wf_modules.findIndex(w => w.id === wfModuleId);

  if (wfModuleIdx === -1) {
    return state;
  }

  let wf_modules = state.workflow.wf_modules.filter(w => w.id !== wfModuleId);

  // If we are deleting the selected module, then set previous module in stack as selected
  let selected_wf_module = state.selected_wf_module;
  if (selected_wf_module === wfModuleId) {
    if (wf_modules.length === 0) {
      selected_wf_module = null;
    } else {
      const newIdx = Math.max(0, wfModuleIdx - 1);
      selected_wf_module = wf_modules[newIdx].id;
    }
  }

  return update(state, {
    workflow: {
      wf_modules: { $set: wf_modules },
    },
    selected_wf_module: { $set: selected_wf_module },
  });
});


// SET_SELECTED_MODULE
// Set the selected module in the workflow
export function setSelectedWfModuleAction(wfModuleId) {
  const state = store.getState()

  if (state.workflow && wfModuleId === state.selected_wf_module) {
    return NOP
  } else {
    const workflow = state.workflow
    const workflowId = workflow ? workflow.id : null

    return {
      type : SET_SELECTED_MODULE,
      payload : {
        promise: api.setSelectedWfModule(workflowId, wfModuleId),
        data: {
          wf_module_id: wfModuleId
        }
      }
    }
  }
}
registerReducerFunc(SET_SELECTED_MODULE + '_PENDING', (state, action) => {
  if (!('selected_wf_module' in state) || (action.payload.wf_module_id !== state.selected_wf_module)) {
    return update(state, {
      selected_wf_module: {$set: action.payload.wf_module_id}
    });
  } else {
    return state;
  }
});


// SET_WF_LIBRARY_COLLAPSE
// Toggle collapse of Module Library
export function setWfLibraryCollapseAction(workflow_id, isCollapsed, isReadOnly) {
  let payload = {
    data : { id: workflow_id, module_library_collapsed: isCollapsed }
  };

  if (!isReadOnly) {
    payload.promise = api.setWfLibraryCollapse(workflow_id, isCollapsed);
  }
  return {
    type : SET_WF_LIBRARY_COLLAPSE,
    payload
  }
}
registerReducerFunc(SET_WF_LIBRARY_COLLAPSE + '_PENDING', (state, action) => {
  return update(state, {
    workflow:
      {module_library_collapsed: {$set: action.payload.module_library_collapsed}
  }});
});



// --- Workflow Module actions ---

// UPDATE_WF_MODULE
// Patch a workflow module with new data

// TODO: We don't validate which fields or types are on
// a WfModule here. The backend will reject nonexistent
// fields, but should we do something on the frontend?
export function updateWfModuleAction(id, data) {
  return {
    type: UPDATE_WF_MODULE,
    payload: {
      promise: api.updateWfModule( id, data ),
      data: {
        id,
        data
      }
    }
  };
}
registerReducerFunc(UPDATE_WF_MODULE + '_PENDING', (state, action) => {
  let moduleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.id
  );

  if (typeof moduleIdx !== 'undefined') {
    return update(state, {
      workflow: {
        wf_modules: {
          [moduleIdx]: { $merge: action.payload.data }
        }
      }
    });
  }

  return state;
});


// SET_WF_MODULE_STATUS
// Change the workflow status (OK, pending, error)
export function setWfModuleStatusAction(wfModuleID, status, error_msg='') {
  return {
    type : SET_WF_MODULE_STATUS,
    payload: {
      id : wfModuleID,
      status : status,
      error_msg: error_msg
    }
  }
}
registerReducerFunc(SET_WF_MODULE_STATUS, (state, action) => {
  if ('wf_modules' in state.workflow) {

    let wfModuleIdx = findIdxByProp(
      state.workflow.wf_modules,
      'id',
      action.payload.id
    );

    let wfModuleRef = state.workflow.wf_modules[wfModuleIdx];

    if ((wfModuleRef.status !== action.payload.status) ||
      (wfModuleRef.status === 'error' && wfModuleRef.error_msg !== action.payload.error_msg)) {

      // Create a copy of the wf_module with new status
      let newWfmProps = {status: action.payload.status, error_msg: action.payload.error_msg};

      return update(state, {
        workflow: {
          wf_modules: {
            [wfModuleIdx]: {$merge: newWfmProps}
          }
        }
      });
    } else {
      return state
    }
  } else {
    return state;
  }
});

export function setWfModuleCollapsedAction(wfModuleID, isCollapsed, isReadOnly) {
  let payload = {
    data : { wf_module_id: wfModuleID, is_collapsed: isCollapsed }
  };

  if (!isReadOnly) {
    payload.promise = api.setWfModuleCollapsed(wfModuleID, isCollapsed);
  }
  return {
    type : SET_WF_MODULE_COLLAPSED,
    payload
  }
}
registerReducerFunc(SET_WF_MODULE_COLLAPSED + '_PENDING', (state, action) => {
  if ('wf_modules' in state.workflow) {
    let wfModuleIdx = findIdxByProp(
      state.workflow.wf_modules,
      'id',
      action.payload.wf_module_id
    );

    if (typeof wfModuleIdx !== 'undefined') {
      return update(state, {
        workflow: {
          wf_modules: {
            [wfModuleIdx]: { is_collapsed: { $set: action.payload.is_collapsed } }
          }
        }
      });
    }
  }

  return state;
});

// --- Parameter actions ---

// SET_PARAM_VALUE

// Internal API, requires all indices
function setParamValueAction_base(state, wfModuleIdx, paramIdx, paramId, newValue) {

  // Suppress changing to the same value (don't trigger expensive HTTP request)
  let oldValue = state.workflow.wf_modules[wfModuleIdx].parameter_vals[paramIdx].value;
  if (newValue.value === oldValue) return NOP

  return {
    type: SET_PARAM_VALUE,
    payload: {
      promise: api.onParamChanged(paramId, newValue),
      data: {
        paramId,
        paramValue: newValue.value
      }
    }
  }
}

// Most common form
export function setParamValueAction(paramId, paramValue) {
  let state = store.getState();
  let { wfModuleIdx, paramIdx } = paramIdToIndices(state.workflow, paramId);
  return setParamValueAction_base(state, wfModuleIdx, paramIdx, paramId, paramValue);
}

// This action creator is used when we don't have a parameter id
export function setParamValueActionByIdName(wfModuleId, paramIdName, paramValue) {
  let state = store.getState();
  let wfModuleIdx = findIdxByProp(state.workflow.wf_modules, 'id', wfModuleId);
  let paramIdx = findParamIdxByIdName(state.workflow.wf_modules[wfModuleIdx], paramIdName);
  let paramId = state.workflow.wf_modules[wfModuleIdx].parameter_vals[paramIdx].id;
  return setParamValueAction_base(state, wfModuleIdx, paramIdx, paramId, paramValue)
}

registerReducerFunc(SET_PARAM_VALUE + '_PENDING', (state, action) => {

  // Find the index of the module in the stack and the parameter in the module
  // We may have done this in the action creator, but don't want to rely on stable indices
  let { wfModuleIdx, paramIdx } = paramIdToIndices(state.workflow, action.payload.paramId);

  if (typeof paramIdx !== 'undefined' ) {

    return update(state, {
      workflow: {
        wf_modules: {
          [wfModuleIdx]: {
            parameter_vals: {
              [paramIdx]: {
                value: { $set: action.payload.paramValue }
              }
            }
          }
        }
      }
    });
  }

  return state;
});

// --- Data Version actions ---

// SET_DATA_VERSION
export function setDataVersionAction(wfModuleId, selectedVersion) {
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
  let wfModuleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.wfModuleId
  );
  return update(state, {
    workflow: {
      wf_modules: {
        [wfModuleIdx]: {
          versions: {
            selected: {$set: action.payload.selectedVersion}
          }
        }
      }
    }
  })
});

// MARK_DATA_VERSIONS_READ
// Called when the user views a version that has a "new data" alert on it
export function markDataVersionsReadAction(id, versions) {
  let versions_to_update = [].concat(versions); // will accept one or many
  return {
    type: MARK_DATA_VERSIONS_READ,
    payload: {
      promise: api.markDataVersionsRead(id, versions_to_update),
      data: {
        id,
        versions_to_update
      }
    }
  };
}
registerReducerFunc(MARK_DATA_VERSIONS_READ + '_PENDING', (state, action) => {
  let wfModuleIdx = findIdxByProp(state.workflow.wf_modules, 'id', action.payload.id);
  if (typeof wfModuleIdx !== 'undefined' &&
    typeof state.workflow.wf_modules[wfModuleIdx].versions !== 'undefined') {
    return update(state, {
      workflow: {
        wf_modules: {
          [wfModuleIdx]: {
            // Take the versions array,
            versions: { versions: { $apply: (versionsArray) => {
              // For each version,
              return versionsArray.map((version) => {
                // If this is a version we want to mark read,
                if (action.payload.versions_to_update.indexOf(version[0]) >= 0) {
                  // Set the 'read' bit to true
                  version[1] = true;
                }
                // Return the version
                return version;
              });
            }}}
          }
        }
      }
    });
  }
  return state;
});

export function clearNotificationsAction(wfModuleId) {
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
  let wfModuleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.wfModuleId
  );
  if (typeof wfModuleIdx !== 'undefined') {
    return update(state, {
      workflow: {
        wf_modules: {
          [wfModuleIdx]: {
            notification_count: {$set: 0}
          }
        }
      }
    });
  }
  return state;
});


// ---- Reducer ----
// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion

export function workflowReducer(state, action) {
  if (!state) {
    state = {}; // initial state. we'll load a workflow soon.
  }

  if (reducerFunc && action.type in reducerFunc) {
    return reducerFunc[action.type](state, action);
  }

  return state;
}
