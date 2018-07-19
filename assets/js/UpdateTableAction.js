import {store, addModuleAction, setParamValueAction, setParamValueActionByIdName} from './workflow-reducer'
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from './utils'

// Unit tests written in individual test.js files per module ex: SortFromTable.test.js

// Map Module id_name to update function and moduleId in workflows.py
const updateModuleMapping = {
  'duplicate-column': {
    updateFunction: updateDuplicateModule,
    moduleId: 'duplicateModuleId'
  },
  'rename-columns': {
    updateFunction: updateRenameModule,
    moduleId: 'renameModuleId'
  },
  'reorder-columns': {
    updateFunction: updateReorderModule,
    moduleId: 'reorderModuleId'
  },
  'sort-from-table': {
    updateFunction: updateSortModule,
    moduleId: 'sortModuleId'
  }
}

// Constants for sort module
const SortTypes = 'String|Number|Date'.split('|')
export const sortDirectionNone = 0
export const sortDirectionAsc = 1
export const sortDirectionDesc = 2

export function updateTableActionModule (wfModuleId, idName, moduleParams) {
  const state = store.getState()

  const existingModule = findModuleWithIdAndIdName(state, wfModuleId, idName)
  if (existingModule) {
    DEPRECATED_ensureSelectedWfModule(store, existingModule) // before state's existingModule changes
    updateModuleMapping[idName].updateFunction(existingModule, moduleParams) // ... changing state's existingModule
  } else {
    const wfModuleIndex = getWfModuleIndexfromId(state, wfModuleId)
    store.dispatch(addModuleAction(state[updateModuleMapping[idName].moduleId], wfModuleIndex + 1))
      .then(fulfilled => {
        const newWfm = fulfilled.value
        updateModuleMapping[idName].updateFunction(newWfm, moduleParams)
      })
  }
}

function updateDuplicateModule (wfm, params) {
  const entriesParam = findParamValByIdName(wfm, 'colnames')
  // if params already exist, check if duplicateColumn already exists
  if (entriesParam.value) {
    if (!(entriesParam.value.split(',').includes(params.duplicateColumnName))) {
      let entries = entriesParam.value + ',' + params.duplicateColumnName
      store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', entries))
    }
    // if duplicateColumnName already in entriesParam, do nothing
  } else {
    store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', params.duplicateColumnName))
  }
}

function updateSortModule (wfm, params) {
  // Must be kept in sync with sortfromtable.json
  const sortTypeIdx = SortTypes.indexOf(params.sortType)
  store.dispatch(setParamValueActionByIdName(wfm.id, 'column', params.sortColumn))
  store.dispatch(setParamValueActionByIdName(wfm.id, 'direction', params.sortDirection))
  store.dispatch(setParamValueActionByIdName(wfm.id, 'dtype', sortTypeIdx))
}

// renameInfo format: {prevName: <current column name in table>, newName: <new name>}

function updateRenameModule (wfm, params) {
  const entriesParam = findParamValByIdName(wfm, 'rename-entries')
  let entries
  if (entriesParam.value) {
    try {
      entries = JSON.parse(entriesParam.value)
    } catch (e) {
      console.warn(e)
      entries = {}
    }
  } else {
    entries = {}
  }
  // If "prevName" in renameInfo exists as a value in edit entries,
  // update that entry (since we are renaming a renamed column)
  let entryExists = false
  for (let k in entries) {
    if (entries[k] === params.renameInfo.prevName) {
      entries[k] = params.renameInfo.newName
      entryExists = true
      break
    }
  }
  // Otherwise, add the new entry to existing entries.
  if (!entryExists) {
    entries[params.renameInfo.prevName] = params.renameInfo.newName
  }
  store.dispatch(setParamValueAction(entriesParam.id, JSON.stringify(entries)))
}

function updateReorderModule (wfm, params) {
  var historyParam = findParamValByIdName(wfm, 'reorder-history')
  var historyStr = historyParam ? historyParam.value.trim() : ''
  var historyEntries = []
  try {
    historyEntries = JSON.parse(historyStr)
  } catch (e) {
    // Something is wrong with our history. Erase it and start over, what else can we do?
  }

  // User must drag two spaces to indicate moving one column right (because drop = place before this column)
  // So to prevent all other code from having to deal with this forever, decrement the index here
  if (params.reorderInfo.to > params.reorderInfo.from) {
    params.reorderInfo.to -= 1
  }

  historyEntries.push(params.reorderInfo)
  store.dispatch(setParamValueAction(historyParam.id, JSON.stringify(historyEntries)))
}
