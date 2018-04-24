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
function updateSortDirection(wfm, sortInfo, sortType) {
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

function updateSortModule(wfm, sortInfo, sortType) {
    //console.log(sortInfo);
    var column = sortInfo.column;
    var columnParam = findParamValByIdName(wfm, "column");
    var typeParam = findParamValByIdName(wfm, "dtype");
    console.log(typeParam);
    //console.log(columnParam)
    // If column changes then we need to change both sort column and type
    if(columnParam.value != column) {
        api.onParamChanged(columnParam.id, {value: column})
            .then(() => {
                api.onParamChanged(typeParam.id, {value: sortType}).then(() => {
                   updateSortDirection(wfm, sortInfo);
                });
            });
    } else {
        updateSortDirection(wfm, sortInfo);
    }
}

export function updateSort(wfModuleId, sortInfo) {
    var state = store.getState();
    //console.log(sortInfo);
    //console.log(state);

    api.getColumns(wfModuleId)
        .then((columns) => {
            let columnInfo = columns.filter((col) => (col.name == sortInfo.column));
            if(columnInfo.length < 1) {
                return;
            }

            // Must be kept in sync with sortfromtable.json
            let sortTypes = "String|Number|Date".split("|")
            let sortType = columnInfo[0].type;
            let sortTypeIdx = sortTypes.indexOf(sortType);
            console.log(sortTypes, sortType);
            var existingSortModule = findModuleWithIdAndIdName(state, wfModuleId, 'sort-from-table')
            if(existingSortModule) {
                //console.log("Sort module exists.");
                updateSortModule(existingSortModule, sortInfo, sortTypeIdx);
                if(existingSortModule.id != wfModuleId) {
                    store.dispatch(setSelectedWfModuleAction(existingSortModule.id));
                }
            } else {
                let wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
                //console.log("New sort module should be created");
                api.addModule(getPageID(), state.sortModuleId, wfModuleIdx + 1)
                    .then((newWfm) => {
                        store.dispatch(setSelectedWfModuleAction(newWfm.id))
                            .then(() => {
                                // A timeout is set to prevent locking up the database
                                setTimeout(() => {updateSortModule(newWfm, sortInfo, sortTypeIdx);}, 200);
                            });
                    });
            }
        });

    //console.log(state);
}