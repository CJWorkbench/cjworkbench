import React from 'react'
import {store, setSelectedWfModuleAction} from "./workflow-reducer";
import {getPageID} from "./utils";
import WorkbenchAPI from './WorkbenchAPI'
import {findModuleWithIdAndIdName, findParamValByIdName} from './EditCells'

var api = WorkbenchAPI();
export function mockAPI(mock_api) {
  api = mock_api;
}

function updateSortModule(wfm, info) {
    console.log(info);
    var column = info.column;
    var columnParam = findParamValByIdName(wfm, "column")
    console.log(columnParam)
    if(columnParam.value != column) {
        api.onParamChanged(columnParam.id, {value: column});
    }

    // Sort direction options: "Select|Ascending|Descending"
    var direction = 0; // Corresponds to "select"
    if(info.direction == 'ASC') {
        direction = 1;
    } else if(info.direction == 'DESC') {
        direction = 2
    }
    var directionParam = findParamValByIdName(wfm, "direction");
    console.log(directionParam)
    if(directionParam.value != direction) {
        api.onParamChanged(directionParam.id, {value: direction});
    }
}

export function updateSort(wfModuleId, sortInfo) {
    var state = store.getState();
    console.log(sortInfo);

    var existingSortModule = findModuleWithIdAndIdName(state, wfModuleId, 'sort-from-table')
    if(existingSortModule) {
        console.log("Sort module exists.");
        updateSortModule(existingSortModule, sortInfo);
    } else {
        console.log("New sort module should be created");
    }

    //console.log(state);
}