import React from 'react'
import {store, setSelectedWfModuleAction} from "./workflow-reducer";
import {getPageID} from './utils'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId} from "./utils";
import WorkbenchAPI from "./WorkbenchAPI";

var api = WorkbenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

function updateReorderModule(module, reorderInfo) {
    var historyParam = findParamValByIdName(module, "reorder-history");
    var historyStr = historyParam ? historyParam.value.trim() : '';
    var historyEntries = []
    try {
        historyEntries = JSON.parse(historyStr);
    } catch(e) {}
    historyEntries.push(reorderInfo);
    api.onParamChanged(historyParam.id, {value: JSON.stringify(historyEntries)});
}

export function updateReorder(wfModuleId, reorderInfo) {
    var state = store.getState();
    const workflowId = state.workflow ? state.workflow.id : null;

    var existingReorderModule = findModuleWithIdAndIdName(state, wfModuleId, 'reorder-columns');
    if(existingReorderModule) {
        if(existingReorderModule.id != wfModuleId) {
            store.dispatch(setSelectedWfModuleAction(existingReorderModule.id));
        }
        updateReorderModule(existingReorderModule, reorderInfo);
    } else {
        let wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
        api.addModule(workflowId, state.reorderModuleId, wfModuleIdx + 1)
            .then((newWfm) => {
                store.dispatch(setSelectedWfModuleAction(newWfm.id));
                updateReorderModule(newWfm, reorderInfo);
            });
    }
}