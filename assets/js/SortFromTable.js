import {store, addModuleAction, setParamValueAction, setParamValueActionByIdName} from "./workflow-reducer";
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from "./utils";

const SortTypes = "String|Number|Date".split("|")

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
function toggleSortDirection(wfm, sortType, reset=false) {
    var directionParam = findParamValByIdName(wfm, "direction");
    let currentDirection = reset ? 0 : parseInt(directionParam.value);
    var nextDirection = getNextSortDirection(currentDirection, sortType);

    store.dispatch(setParamValueAction(directionParam.id, nextDirection));
}

function updateSortModule(wfm, sortColumn, sortType) {
    const columnParam = findParamValByIdName(wfm, "column");
    const isDifferentColumn = columnParam.value !== sortColumn;

    store.dispatch(setParamValueActionByIdName(wfm.id, 'column', sortColumn));
    store.dispatch(setParamValueActionByIdName(wfm.id, 'dtype', sortType));
    toggleSortDirection(wfm, sortType, isDifferentColumn);
}

export function updateSort(wfModuleId, sortColumn, sortType) {
    const state = store.getState();

    // Must be kept in sync with sortfromtable.json
    const sortTypeIdx = SortTypes.indexOf(sortType);
    const existingModule = findModuleWithIdAndIdName(state, wfModuleId, 'sort-from-table')
    if (existingModule) {
        DEPRECATED_ensureSelectedWfModule(store, existingModule); // before state's existingModule changes
        updateSortModule(existingModule, sortColumn, sortTypeIdx); // ... changing state's existingModule
    } else {
        const wfModuleIndex = getWfModuleIndexfromId(state, wfModuleId);
        store.dispatch(addModuleAction(state.sortModuleId, wfModuleIndex + 1))
            .then(fulfilled => {
                const newWfm = fulfilled.value;
                updateSortModule(newWfm, sortColumn, sortTypeIdx);
            });
    }
}
