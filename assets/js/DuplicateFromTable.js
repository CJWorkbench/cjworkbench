import {store, addModuleAction, setParamValueAction, setParamValueActionByIdName} from './workflow-reducer'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from './utils'

function updateDuplicateModule (wfm, duplicateColumn) {
  const entriesParam = findParamValByIdName(wfm, 'colnames')
  // if params already exist, check if duplicateColumn already exists
  if (entriesParam.value) {
    if (!(entriesParam.value.split(',').includes(duplicateColumn))) {
      let entries = entriesParam.value + ',' + duplicateColumn
      store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', entries))
    }
    // if duplicateColumn already in entriesParam, do nothing
  } else {
    store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', duplicateColumn))
  }
}

export function updateDuplicate (wfModuleId, duplicateColumn) {
  const state = store.getState()

  const existingModule = findModuleWithIdAndIdName(state, wfModuleId, 'duplicate-column-from-table')
  if (existingModule) {
    DEPRECATED_ensureSelectedWfModule(store, existingModule) // before state's existingModule changes
    updateDuplicateModule(existingModule, duplicateColumn) // ... changing state's existingModule
  } else {
    const wfModuleIndex = getWfModuleIndexfromId(state, wfModuleId)
    store.dispatch(addModuleAction(state.duplicateModuleId, wfModuleIndex + 1))
      .then(fulfilled => {
        const newWfm = fulfilled.value
        updateDuplicateModule(newWfm, duplicateColumn)
      })
  }
}
