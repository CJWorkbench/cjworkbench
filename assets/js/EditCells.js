// Code required to add a cell edit.
// Including creating an Edit Cells module if needed, and syncing to server
import React from 'react'
import {store} from "./workflow-reducer";
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from "./utils";
import WorkbenchAPI from './WorkbenchAPI'

var api = WorkbenchAPI(); // var so it can be mocked for testing
export function mockAPI(mock_api) {
  api = mock_api;
}

// TODO: Approximately from here down, move into reducer

function addEditCellWfModule(state, insertBefore) {
  const moduleId =  state.editCellsModuleId;
  const workflowId = state.workflow ? state.workflow.id : null;
  return (
      api.addModule(workflowId, moduleId, insertBefore)
  )
}

// Given an Edit Cells module, add a single edit to its list of edited cells, and set this param on server
function addEditToEditCellsModule(wfm, edit) {
  var state = store.getState();
  var param = findParamValByIdName(wfm, 'celledits');

  var edit_json = param.value;
  var edits = [];
  try {
    edits = JSON.parse(edit_json);
  } catch(err) {
    edits = [];    // most likely empty parameter value, but recover parse errors to empty list
  }

  // Add this edit and update the server
  // TODO: tell server not to tell us to reload workflow, we already did an optimistic update
  edits.push(edit);
  var new_edit_json = JSON.stringify(edits);
  api.onParamChanged(param.id, {value: new_edit_json});
}


// User edited output of wfModuleId
export function addCellEdit(wfModuleId, edit) {
  const state = store.getState();

  const existingEditCellsWfm = findModuleWithIdAndIdName(state, wfModuleId, 'editcells');
  if (existingEditCellsWfm) {
    // Adding edit to existing module
    addEditToEditCellsModule(existingEditCellsWfm, edit);
    DEPRECATED_ensureSelectedWfModule(store, existingEditCellsWfm);
  } else {
    // Create a new module after current one and add edit to it
    const wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);

    addEditCellWfModule(state, wfModuleIdx+1)
      .then((newWfm)=> {
        // add edit to newly created module and select it
        addEditToEditCellsModule(newWfm, edit);
        DEPRECATED_ensureSelectedWfModule(store, newWfm);
      });
  }
}
