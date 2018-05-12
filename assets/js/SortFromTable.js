import React from 'react'
import {store, setSelectedWfModuleAction, addModuleAction, setParamValueAction} from "./workflow-reducer";
import {getPageID} from "./utils";
import WorkbenchAPI from './WorkbenchAPI'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId} from "./utils";

var api = WorkbenchAPI();
export function mockAPI(mock_api) {
  api = mock_api;
}

function getNextSortDirection(current, sortType) {
    // Determines what the next sort direction is based on current direction
    // and data type
    // Sort directions: 0 -> NOP, 1 -> Ascending, 2 -> Descending
    // Sort types: 0 -> String, 1 -> Number, 2 -> Date

    let SORT_TYPE_STRING = 0;
    let SORT_TYPE_NUMBER = 1;
    let SORT_TYPE_DATE = 2;

    if(sortType == SORT_TYPE_STRING) {
        // String: NOP (0) -> ASC (1) -> DESC (2)
        return (current + 1) % 3;
    }
    // Number and Date: NOP (0) -> DESC (2) -> ASC (1)
    return (current + 2) % 3;
}

// Wrapper function for changing sort direction, since it needs to be used twice.
function updateSortDirection(wfm, sortColumn, sortType, reset=false) {
    var directionParam = findParamValByIdName(wfm, "direction");
    let currentDirection = reset ? 0 : parseInt(directionParam.value);
    var nextDirection = getNextSortDirection(currentDirection, sortType)

    api.onParamChanged(directionParam.id, {value: nextDirection});
}

function updateSortModule(wfm, sortColumn, sortType) {
    var column = sortColumn;
    var columnParam = findParamValByIdName(wfm, "column");
    var typeParam = findParamValByIdName(wfm, "dtype");
    // If column changes then we need to change both sort column and type
    if(columnParam.value != column) {
        api.onParamChanged(columnParam.id, {value: column})
            .then(() => {
                api.onParamChanged(typeParam.id, {value: sortType})
                    .then(() => {
                        updateSortDirection(wfm, sortColumn, sortType, true);
                    });
            });
    } else {
        updateSortDirection(wfm, sortColumn, sortType, false);
    }
}

export function updateSort(wfModuleId, sortColumn, sortType) {
    var state = store.getState();
    const workflowId = state.workflow ? state.workflow.id : null;

    // Must be kept in sync with sortfromtable.json
    let sortTypes = "String|Number|Date".split("|")
    let sortTypeIdx = sortTypes.indexOf(sortType);
    var existingSortModule = findModuleWithIdAndIdName(state, wfModuleId, 'sort-from-table')
    if(existingSortModule) {
        if(existingSortModule.id != wfModuleId) {
            store.dispatch(setSelectedWfModuleAction(existingSortModule.id));
        }
        updateSortModule(existingSortModule, sortColumn, sortTypeIdx);
    } else {
        let wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
        // I have tried but using the reducer introduces odd bugs
        // w.r.t selecting the new sort module, it bounces to the new module
        // and then bounces back
        api.addModule(workflowId, state.sortModuleId, wfModuleIdx + 1)
            .then((newWfm) => {
                store.dispatch(setSelectedWfModuleAction(newWfm.id));
                updateSortModule(newWfm, sortColumn, sortTypeIdx);
            });
    }
}