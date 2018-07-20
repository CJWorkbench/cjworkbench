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

export function updateTableActionModule (wfModuleId, idName, ...params) {
  const state = store.getState()

  const existingModule = findModuleWithIdAndIdName(state, wfModuleId, idName)
  if (existingModule) {
    DEPRECATED_ensureSelectedWfModule(store, existingModule) // before state's existingModule changes
    updateModuleMapping[idName].updateFunction(existingModule, params) // ... changing state's existingModule
  } else {
    const wfModuleIndex = getWfModuleIndexfromId(state, wfModuleId)
    store.dispatch(addModuleAction(state[updateModuleMapping[idName].moduleId], wfModuleIndex + 1))
      .then(fulfilled => {
        const newWfm = fulfilled.value
        updateModuleMapping[idName].updateFunction(newWfm, params)
      })
  }
}

function updateDuplicateModule (wfm, params) {
  const entriesParam = findParamValByIdName(wfm, 'colnames')
  const duplicateColumnName = params[0]

  // if params already exist, check if duplicateColumnName already exists
  if (entriesParam.value) {
    if (!(entriesParam.value.split(',').includes(duplicateColumnName))) {
      let entries = entriesParam.value + ',' + duplicateColumnName
      store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', entries))
    }
    // if duplicateColumnName already in entriesParam, do nothing
  } else {
    store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', duplicateColumnName))
  }
}

function updateSortModule (wfm, params) {
  const sortColumn = params[0]
  const sortType = params[1]
  const sortDirection = params[2]

  // Must be kept in sync with sortfromtable.json
  const sortTypeIdx = SortTypes.indexOf(sortType)
  store.dispatch(setParamValueActionByIdName(wfm.id, 'column', sortColumn))
  store.dispatch(setParamValueActionByIdName(wfm.id, 'direction', sortDirection))
  store.dispatch(setParamValueActionByIdName(wfm.id, 'dtype', sortTypeIdx))
}

// renameInfo format: {prevName: <current column name in table>, newName: <new name>}

function updateRenameModule (wfm, params) {
  const renameInfo = params[0]
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
    if (entries[k] === renameInfo.prevName) {
      entries[k] = renameInfo.newName
      entryExists = true
      break
    }
  }
  // Otherwise, add the new entry to existing entries.
  if (!entryExists) {
    entries[renameInfo.prevName] = renameInfo.newName
  }
  store.dispatch(setParamValueAction(entriesParam.id, JSON.stringify(entries)))
}

function updateReorderModule (wfm, params) {
  const reorderInfo = params[0]
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
  if (reorderInfo.to > reorderInfo.from) {
    reorderInfo.to -= 1
  }

  historyEntries.push(reorderInfo)
  store.dispatch(setParamValueAction(historyParam.id, JSON.stringify(historyEntries)))
}
