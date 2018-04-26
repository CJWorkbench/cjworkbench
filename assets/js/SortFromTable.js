import React from 'react'
import {store, setSelectedWfModuleAction} from "./workflow-reducer";
import {getPageID} from "./utils";
import WorkbenchAPI from './WorkbenchAPI'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId} from './EditCells'

var api = WorkbenchAPI();
export function mockAPI(mock_api) {
  api = mock_api;
}

function getNextSortDirection(current, sortType) {
    // Determines what the next sort direction is based on current direction
    // and data type
    // Sort directions: 0 -> NOP, 1 -> Ascending, 2 -> Descending
    // Sort types: 0 -> String, 1 -> Number, 2 -> Date
    var next = 0;
    if(current == 0) {
        if(sortType == 0) {
            // String uses ascending by default
            next = 1;
        } else {
            // Numbers and dates use descending by default
            next = 2;
        }
    } else if(current == 1) {
        if(sortType == 0) {
            // For string
            next = 2;
        } else {
            // For numbers and dates
            next = 0;
        }
    } else {
        if(sortType == 0) {
            next = 0;
        } else {
            next = 1;
        }
    }
    return next;
}

// Wrapper function for changing sort direction, since it needs to be used twice.
function updateSortDirection(wfm, sortInfo, sortType, reset=false) {

    // I left this code in because the implementation below can
    // cause the UI to show the wrong arrow for a second before
    // the database fully updates. We can talk about which behavior
    // is preferable later.
    /*
    var direction = 0; // Corresponds to "select"
    if(sortInfo.direction == 'ASC') {
        direction = 1;
    } else if(sortInfo.direction == 'DESC') {
        direction = 2
    }
    */

    // Sort directions: 0 -> NOP, 1 -> Ascending, 2 -> Descending
    var directionParam = findParamValByIdName(wfm, "direction");
    let currentDirection = reset ? 0 : parseInt(directionParam.value);
    var nextDirection = getNextSortDirection(currentDirection, sortType)

    api.onParamChanged(directionParam.id, {value: nextDirection});
}

function updateSortModule(wfm, sortInfo, sortType) {
    var column = sortInfo.column;
    var columnParam = findParamValByIdName(wfm, "column");
    var typeParam = findParamValByIdName(wfm, "dtype");
    // If column changes then we need to change both sort column and type
    if(columnParam.value != column) {
        api.onParamChanged(columnParam.id, {value: column})
            .then(() => {
                api.onParamChanged(typeParam.id, {value: sortType}).then(() => {
                    // Timeout to prevent database locked 500 errors.
                    setTimeout(() => {
                        updateSortDirection(wfm, sortInfo, sortType, true);
                    }, 200);
                });
            });
    } else {
        updateSortDirection(wfm, sortInfo, sortType);
    }
}

export function updateSort(wfModuleId, sortInfo) {
    var state = store.getState();

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
            var existingSortModule = findModuleWithIdAndIdName(state, wfModuleId, 'sort-from-table')
            if(existingSortModule) {
                updateSortModule(existingSortModule, sortInfo, sortTypeIdx);
                if(existingSortModule.id != wfModuleId) {
                    store.dispatch(setSelectedWfModuleAction(existingSortModule.id));
                }
            } else {
                let wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId);
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
}