import {store, addModuleAction, setParamValueAction, setParamValueActionByIdName} from "./workflow-reducer";
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from "./utils";

const SortTypes = "String|Number|Date".split("|")
export const sortDirectionNone = 0
export const sortDirectionAsc = 1
export const sortDirectionDesc = 2

function updateSortModule(wfm, sortColumn, sortType, sortDirection) {
    store.dispatch(setParamValueActionByIdName(wfm.id, 'column', sortColumn));
    store.dispatch(setParamValueActionByIdName(wfm.id, 'direction', sortDirection));
    store.dispatch(setParamValueActionByIdName(wfm.id, 'dtype', sortType));
}

export function updateSort(wfModuleId, sortColumn, sortType, sortDirection) {
    const state = store.getState();

    // Must be kept in sync with sortfromtable.json
    const sortTypeIdx = SortTypes.indexOf(sortType);
    const existingModule = findModuleWithIdAndIdName(state, wfModuleId, 'sort-from-table')
    if (existingModule) {
        DEPRECATED_ensureSelectedWfModule(store, existingModule); // before state's existingModule changes
        updateSortModule(existingModule, sortColumn, sortTypeIdx, sortDirection); // ... changing state's existingModule
    } else {
        const wfModuleIndex = getWfModuleIndexfromId(state, wfModuleId);
        store.dispatch(addModuleAction(state.sortModuleId, wfModuleIndex + 1))
            .then(fulfilled => {
                const newWfm = fulfilled.value;
                updateSortModule(newWfm, sortColumn, sortTypeIdx, sortDirection);
            });
    }
}
