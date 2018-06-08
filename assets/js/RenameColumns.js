import React from 'react'
import {store, setSelectedWfModuleAction} from "./workflow-reducer";
import {getPageID} from './utils'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId} from "./utils";
import WorkBenchAPI from './WorkbenchAPI'

var api = WorkBenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

//renameInfo format: {prevName: <current column name in table>, newName: <new name>}

function updateRenameModule(module, renameInfo, isNew=false) {
    var entriesParam = findParamValByIdName(module, 'rename-entries');
    var existingEntries = {}
    try {
        existingEntries = JSON.parse(entriesParam.value.trim());
    } catch(e) {}
    // If "prevName" in renameInfo exists as a value in edit entries,
    // update that entry (since we are renaming a renamed column)
    var entryExists = false;
    for(let k in existingEntries) {
        if(existingEntries[k] == renameInfo.prevName) {
            existingEntries[k] = renameInfo.newName;
            entryExists = true;
            break;
        }
    }
    // Otherwise, add the new entry to existing entries.
    if(!entryExists) {
        existingEntries[renameInfo.prevName] = renameInfo.newName;
    }
    if(isNew) {
        var showAllParam = findParamValByIdName(module, 'display-all');
        try {
            api.onParamChanged(showAllParam.id, {value: false})
                .then(api.onParamChanged(entriesParam.id, {value: JSON.stringify(existingEntries)}));
        } catch(e) {}
    }
    else {
        api.onParamChanged(entriesParam.id, {value: JSON.stringify(existingEntries)});
    }
}

export function updateRename(wfModuleId, renameInfo) {
    var state = store.getState();
    console.log(state);
    const workflowId = state.workflow ? state.workflow.id : null;

    var existingRenameModule = findModuleWithIdAndIdName(state, wfModuleId, 'rename-columns');
    if(existingRenameModule) {
        if(existingRenameModule.id != wfModuleId) {
            store.dispatch(setSelectedWfModuleAction(existingRenameModule.id));
        }
        updateRenameModule(existingRenameModule, renameInfo);
    } else {
        let wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
        api.addModule(workflowId, state.renameModuleId, wfModuleIdx + 1)
            .then((newWfm) => {
                // We set the parameters first and then switch to the new module
                // to prevent it loading all columns in its initial rendering
                // (which would be the case if it's added from the module library)
                updateRenameModule(newWfm, renameInfo, true);
                store.dispatch(setSelectedWfModuleAction(newWfm.id));
            });
    }
}