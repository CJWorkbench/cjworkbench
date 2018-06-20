import {store, addModuleAction, setParamValueAction} from "./workflow-reducer";
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from "./utils";

//renameInfo format: {prevName: <current column name in table>, newName: <new name>}

function updateRenameModule(module, renameInfo, isNew=false) {
    const entriesParam = findParamValByIdName(module, 'rename-entries');
    let entries;
    if (entriesParam.value) {
        try {
            entries = JSON.parse(entriesParam.value);
        } catch (e) {
            console.warn(e);
            entries = {};
        }
    } else {
        entries = {};
    }
    // If "prevName" in renameInfo exists as a value in edit entries,
    // update that entry (since we are renaming a renamed column)
    let entryExists = false;
    for (let k in entries) {
        if (entries[k] == renameInfo.prevName) {
            entries[k] = renameInfo.newName;
            entryExists = true;
            break;
        }
    }
    // Otherwise, add the new entry to existing entries.
    if (!entryExists) {
        entries[renameInfo.prevName] = renameInfo.newName;
    }
    store.dispatch(setParamValueAction(entriesParam.id, JSON.stringify(entries)));
}

export function updateRename(wfModuleId, renameInfo) {
    const state = store.getState();

    const existingModule = findModuleWithIdAndIdName(state, wfModuleId, 'rename-columns');
    if (existingModule) {
        DEPRECATED_ensureSelectedWfModule(store, existingModule); // before state's existingModule changes
        updateRenameModule(existingModule, renameInfo, false); // ... changing state's existingModule
    } else {
        const wfModuleIndex = getWfModuleIndexfromId(state, wfModuleId);
        store.dispatch(addModuleAction(state.renameModuleId, wfModuleIndex + 1))
            .then(fulfilled => {
                const newWfm = fulfilled.value;
                updateRenameModule(newWfm, renameInfo, true);
            });
    }
}
