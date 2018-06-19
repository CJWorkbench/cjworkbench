import React from 'react'
import {store} from "./workflow-reducer";
import {getPageID} from './utils'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from "./utils";
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
    const state = store.getState();
    const workflowId = state.workflow ? state.workflow.id : null;

    const existingReorderModule = findModuleWithIdAndIdName(state, wfModuleId, 'reorder-columns');
    if (existingReorderModule) {
        updateReorderModule(existingReorderModule, reorderInfo);
        DEPRECATED_ensureSelectedWfModule(store, existingReorderModule);
    } else {
        const wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
        api.addModule(workflowId, state.reorderModuleId, wfModuleIdx + 1)
            .then((newWfm) => {
                updateReorderModule(newWfm, reorderInfo);
                DEPRECATED_ensureSelectedWfModule(store, newWfm);
            });
    }
}
