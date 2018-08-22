import {store, addModuleAction, setParamValueAction, setParamValueActionByIdName, setSelectedWfModuleAction} from './workflow-reducer'
import {findParamValByIdName} from './utils'

// Unit tests written in individual test.js files per module ex: SortFromTable.test.js

// Map Module id_name to update function and moduleId in workflows.py
export const updateModuleMapping = {
  'selectcolumns':    updateSelectModule,
  'duplicate-column': updateDuplicateModule,
  'filter':           updateFilterModule,
  'editcells':        addEditToEditCellsModule,
  'rename-columns':   updateRenameModule,
  'reorder-columns':  updateReorderModule,
  'sort-from-table':  updateSortModule,
  'extract-numbers':  updateExtractNumbersModule,
  'clean-text':       updateCleanTextModule
}

// Constants for sort module
const SortTypes = 'text|number|datetime'.split('|')
export const sortDirectionNone = 0
export const sortDirectionAsc = 1
export const sortDirectionDesc = 2

// Constants for select module
export const selectColumnDrop = 0
export const selectColumnKeep = 1

// Constant for extract numbers module
export const extractNumberAny = 0

function findModuleIdByIdName (state, moduleIdName) {
  return state.updateTableModuleIds[moduleIdName] || null
}

// Find if a module of moduleId exists as or is next to module with focusWfModuleId
function findModuleWithIds (state, focusWfModuleId, moduleId) {
  const { workflow, wfModules } = state

  // validIdsOrNulls: [ 2, null, null, 65 ] means indices 0 and 3 are for
  // desired module (and have wfModuleIds 2 and 64), 1 and 2 aren't for
  // desired module
  const validIdsOrNulls = workflow.wf_modules
    .map(id => (wfModules[String(id)].module_version || {}).module === moduleId ? id : null)

  const focusIndex = workflow.wf_modules.indexOf(focusWfModuleId)
  if (focusIndex === -1) return null

  // Are we already focused on a valid WfModule?
  const atFocusIndex = validIdsOrNulls[focusIndex]
  if (atFocusIndex !== null) return wfModules[String(atFocusIndex)]

  // Is the _next_ wfModule valid? If so, return that
  const nextIndex = focusIndex + 1
  const atNextIndex = validIdsOrNulls[nextIndex]
  if (atNextIndex !== null) return wfModules[String(atNextIndex)]

  // Nope, no target module with moduleIdName where we need it
  return null
}

function ensureSelectedWfModule (state, wfModule) {
  const current = state.selected_wf_module
  let wanted = state.workflow ? state.workflow.wf_modules.indexOf(wfModule.id) : null
  if (wanted === -1) wanted = null

  if (wanted !== null && wanted !== current) {
    store.dispatch(setSelectedWfModuleAction(wanted));
  }
}

export function updateTableActionModule (wfModuleId, idName, forceNewModule, params) {
  const state = store.getState()
  // Check if module imported
  const moduleId = findModuleIdByIdName(state, idName)
  if (moduleId === null) {
    window.alert("Module '" + idName + "' not imported.")
    return
  }
  const existingModule = findModuleWithIds(state, wfModuleId, moduleId)
  if (existingModule && !forceNewModule) {
    ensureSelectedWfModule(state, existingModule) // before state's existingModule changes
    updateModuleMapping[idName](existingModule, params) // ... changing state's existingModule
  } else {
    const wfModuleIndex = state.workflow.wf_modules.indexOf(wfModuleId)
    store.dispatch(addModuleAction(moduleId, wfModuleIndex + 1))
      .then(fulfilled => {
        const newWfm = fulfilled.value.data.wfModule
        updateModuleMapping[idName](newWfm, params)
      })
  }
}

// TODO this can be the model for a default multicolumn handler.
// Will need to pass module name
function updateCleanTextModule (wfm, params) {
  let existingColumns = findParamValByIdName(wfm, 'colnames')
  let newColumn = params.columnKey

  if (existingColumns.value) {
    // Do nothing if column already exists
    if (existingColumns.value.split(',').includes(newColumn)) {}
    else {updateTableActionModule(wfm.id, 'clean-text', true, params)}
  }
  else {
    store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', params.columnKey))
  }
}

function updateExtractNumbersModule (wfm, params) {
  let extractedColumns = findParamValByIdName(wfm, 'colnames')

  if (extractedColumns.value) {
    let extract = findParamValByIdName(wfm, 'extract').value
    let formatType = findParamValByIdName(wfm, 'type_format').value
    let replaceType = findParamValByIdName(wfm, 'type_replace').value
    // If column already an existing module parameter, do nothing
    if (extractedColumns.value.split(',').includes(params.columnKey)) {}
    // If existing module not defaults, force new
    else if ((extract) | (formatType !== 0) | (replaceType !== 0)) {
      updateTableActionModule(wfm.id, 'extract-numbers', true, params)
    }
    else {
      let newColumns = extractedColumns.value + ',' + params.columnKey
      store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', newColumns))
    }
  }
  // New module with extract type 'Any'
  else {
    store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', params.columnKey))
    store.dispatch(setParamValueActionByIdName(wfm.id, 'type', extractNumberAny))
  }
}

function updateFilterModule (wfm, params) {
  store.dispatch(setParamValueActionByIdName(wfm.id, 'column', params.columnKey))
}

function updateSelectModule (wfm, params) {
  let selectedColumns = findParamValByIdName(wfm, 'colnames')
  const action = findParamValByIdName(wfm, 'drop_or_keep')
  const dropColumnName = params.columnKey

  // Case: If module exists and drop already selected
  if (selectedColumns.value && action.value === selectColumnDrop) {
    if (!(selectedColumns.value.split(',').includes(dropColumnName))) {
      let entries = selectedColumns.value + ',' + dropColumnName
      store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', entries))
    }
  }
  // Case: If module exists and keep already selected, deselect dropColumnName
  else if (selectedColumns.value && action.value === selectColumnKeep) {
    selectedColumns = selectedColumns.value.split(',')
    let dropColumnNameIdx = selectedColumns.indexOf(dropColumnName)
    if (dropColumnNameIdx > -1) {
      selectedColumns.splice(dropColumnNameIdx, 1)
      store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', selectedColumns.toString()))
      store.dispatch(setParamValueActionByIdName(wfm.id, 'drop_or_keep', selectColumnKeep))
    }
  }
  // Case: If no existing module
  else if (!selectedColumns.value) {
    store.dispatch(setParamValueActionByIdName(wfm.id, 'colnames', dropColumnName))
    store.dispatch(setParamValueActionByIdName(wfm.id, 'drop_or_keep', selectColumnDrop))
  }
}

function addEditToEditCellsModule (wfm, params) {
  const param = findParamValByIdName(wfm, 'celledits')
  const edit = params
  let edits

  if (param.value) {
    try {
      edits = JSON.parse(param.value)
      // Remove the previous edit to the same cell
      let idx = edits.findIndex((element) => {
        return element.row === params.row && element.col === params.col
      })
      if (idx > -1) {
        edits.splice(idx, idx + 1)
      }
    } catch (err) {
      console.error(err)
      edits = []
    }
  } else {
    edits = []
  }

  // Add this edit and update the server
  edits.push(edit)
  store.dispatch(setParamValueAction(param.id, JSON.stringify(edits)))
}

function updateDuplicateModule (wfm, params) {
  const entriesParam = findParamValByIdName(wfm, 'colnames')
  const duplicateColumnName = params.columnKey

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
  // Must be kept in sync with sortfromtable.json
  const sortTypeIdx = SortTypes.indexOf(params.sortType)
  store.dispatch(setParamValueActionByIdName(wfm.id, 'column', params.columnKey))
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
    if (entries[k] === params.prevName) {
      entries[k] = params.newName
      entryExists = true
      break
    }
  }
  // Otherwise, add the new entry to existing entries.
  if (!entryExists) {
    entries[params.prevName] = params.newName
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
  if (params.to > params.from) {
    params.to -= 1
  }

  historyEntries.push(params)
  store.dispatch(setParamValueAction(historyParam.id, JSON.stringify(historyEntries)))
}
