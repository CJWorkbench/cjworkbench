// Code required to add a cell edit.
// Including creating an Edit Cells module if needed, and syncing to server
import {store, addModuleAction, setParamValueAction} from "./workflow-reducer";
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from "./utils";

// TODO: Approximately from here down, move into reducer

// Given an Edit Cells module, add a single edit to its list of edited cells, and set this param on server
function addEditToEditCellsModule(wfm, edit) {
  const param = findParamValByIdName(wfm, 'celledits');

  let edits;
  if (param.value) {
    try {
      edits = JSON.parse(param.value);
    } catch (err) {
      console.error(err);
      edits = [];
    }
  } else {
    edits = [];
  }

  // Add this edit and update the server
  edits.push(edit);
  store.dispatch(setParamValueAction(param.id, JSON.stringify(edits)));
}


// User edited output of wfModuleId
export function addCellEdit(wfModuleId, edit) {
  const state = store.getState();

  const existingModule = findModuleWithIdAndIdName(state, wfModuleId, 'editcells');
  if (existingModule) {
    // Add edit to existing module
    DEPRECATED_ensureSelectedWfModule(store, existingModule); // before state's existingModule changes
    addEditToEditCellsModule(existingModule, edit); // ... changing state's existingModule
  } else {
    // Create a new module after current one and add edit to it
    const wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
    store.dispatch(addModuleAction(state.editCellsModuleId, wfModuleIdx + 1))
      .then(fulfilled => {
          const newWfm = fulfilled.value;
          addEditToEditCellsModule(newWfm, edit);
      });
  }
}
