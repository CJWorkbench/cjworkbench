import React from 'react'
import {store, setSelectedWfModuleAction} from "./workflow-reducer";
import {getPageID} from "./utils";
import WorkbenchAPI from './WorkbenchAPI'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId} from './EditCells'

var api = WorkbenchAPI();
export function mockAPI(mock_api) {
  api = mock_api;
}

// Wrapper function for changing sort direction, since it needs to be used twice.
function updateSortDirection(wfm, sortInfo) {
    var direction = 0; // Corresponds to "select"
    if(sortInfo.direction == 'ASC') {
        direction = 1;
    } else if(sortInfo.direction == 'DESC') {
        direction = 2
    }
    var directionParam = findParamValByIdName(wfm, "direction");
    console.log(directionParam)
    if(directionParam.value != direction) {
        api.onParamChanged(directionParam.id, {value: direction});
    }
}

function updateSortModule(wfm, sortInfo, callback=null) {
    //console.log(sortInfo);
    var column = sortInfo.column;
    var columnParam = findParamValByIdName(wfm, "column")
    //console.log(columnParam)
    if(columnParam.value != column) {
        api.onParamChanged(columnParam.id, {value: column})
            .then(() => {
                updateSortDirection(wfm, sortInfo);
            });
    } else {
        updateSortDirection(wfm, sortInfo);
    }
}

export function updateSort(wfModuleId, sortInfo) {
    var state = store.getState();
    console.log(sortInfo);
    console.log(state);

    var existingSortModule = findModuleWithIdAndIdName(state, wfModuleId, 'sort-from-table')
    if(existingSortModule) {
        //console.log("Sort module exists.");
        updateSortModule(existingSortModule, sortInfo);
        if(existingSortModule.id != wfModuleId) {
            store.dispatch(setSelectedWfModuleAction(existingSortModule.id));
        }
    } else {
        let wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
        //console.log("New sort module should be created");
        api.addModule(getPageID(), state.sortModuleId, wfModuleIdx + 1)
            .then((newWfm) => {
                store.dispatch(setSelectedWfModuleAction(newWfm.id))
                    .then(() => {setTimeout(() => {updateSortModule(newWfm, sortInfo);}, 200);});
            })
    }

    //console.log(state);
}