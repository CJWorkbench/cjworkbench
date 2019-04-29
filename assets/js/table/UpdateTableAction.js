import { addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

/**
 * Module param-building functions per id_name.
 *
 * Each function has the signature (oldParams, params), and it should
 * return new params or null.
 *
 * `oldParams` will be `null` if this is a new module.
 *
 * Watch out: these param builders are NOT all used in the same way! For
 * example, editcells' "params" is used to add an _edit_, not overwrite an
 * "edits" param. In effect, this is a bunch of functions with completely
 * different purposes but with the same calling convention (kinda like Redux
 * reducers.) Most are used in the column drop-down menu. TODO move the others
 * elsewhere.
 */
export const moduleParamsBuilders = {
  'selectcolumns': buildSelectColumnsParams,
  'duplicatecolumns': genericAddColumn('colnames', false),
  'filter': buildFilterParams,
  'editcells': buildEditCellsParams,
  'renamecolumns': buildRenameColumnsParams,
  'reordercolumns': buildReorderColumnsParams,
  'sort': buildSortColumnsParams,
  'converttexttonumber': genericAddColumn('colnames', false),
  'clean-text': genericAddColumn('colnames', true),
  'convert-date': genericAddColumn('colnames', false),
  'converttotext': genericAddColumn('colnames', true),
  'formatnumbers': genericAddColumn('colnames', true)
}

/**
 * Return { id, params, isNext } of _this_ WfModule or the one _after_ it, matching moduleIdName.
 *
 * Return `null` if this or the next WfModule does not match moduleIdName.
 */
function findWfModuleWithIds (state, focusWfModuleId, moduleIdName) {
  const { tabs, wfModules, modules } = state

  if (!(moduleIdName in modules)) {
    throw new Error(`Cannot find module '${moduleIdName}'`)
  }

  const wfModule = wfModules[String(focusWfModuleId)]
  const tabSlug = wfModule.tab_slug
  const tab = tabs[tabSlug]

  // validIdsOrNulls: [ 2, null, null, 65 ] means indices 0 and 3 are for
  // desired module (and have wfModuleIds 2 and 64), 1 and 2 aren't for
  // desired module
  const validIdsOrNulls = tab.wf_module_ids
    .map(id => wfModules[String(id)].module === moduleIdName ? id : null)

  const focusIndex = tab.wf_module_ids.indexOf(focusWfModuleId)
  if (focusIndex === -1) return null

  // Are we already focused on a valid WfModule?
  const atFocusIndex = validIdsOrNulls[focusIndex]
  if (atFocusIndex !== null) {
    const wfModule = wfModules[String(atFocusIndex)]
    return {
      id: atFocusIndex,
      params: wfModule.params,
      isNext: false
    }
  }

  // Is the _next_ wfModule valid? If so, return that
  const nextIndex = focusIndex + 1
  const atNextIndex = nextIndex >= validIdsOrNulls.length ? null : validIdsOrNulls[nextIndex]
  if (atNextIndex !== null) {
    const wfModule = wfModules[String(atNextIndex)]
    return {
      id: atNextIndex,
      params: wfModule.params,
      isNext: true
    }
  }

  // Nope, no target module with moduleIdName where we need it
  return null
}

/**
 * Adds or edits a module, given `wfModuleId` as the selected table.
 *
 * This is a reducer action that delegates to `addModuleAction`, `setSelectedWfModuleAction` and `
 */
export function updateTableAction (wfModuleId, idName, forceNewModule, params) {
  return (dispatch, getState) => {
    const state = getState()

    if (!(idName in state.modules)) {
      window.alert("Module '" + idName + "' not imported.")
      return
    }

    const existingWfModule = forceNewModule ? null : findWfModuleWithIds(state, wfModuleId, idName)
    const newParams = moduleParamsBuilders[idName](existingWfModule ? existingWfModule.params : null, params)

    if (existingWfModule && !forceNewModule) {
      if (existingWfModule.id !== wfModuleId) {
        dispatch(setSelectedWfModuleAction(existingWfModule.id))
      }
      if (newParams) {
        dispatch(setWfModuleParamsAction(existingWfModule.id, newParams))
      }
    } else {
      dispatch(addModuleAction(idName, { afterWfModuleId: wfModuleId }, newParams))
    }
  }
}

function buildSelectColumnsParams (oldParams, params) {
  if (Object.keys(params).length === 0) {
    // A bit of a hack: if we call this with no params, we're just adding
    // an empty select-columns module with default params.
    return {}
  }

  const colnames = oldParams ? oldParams.colnames.split(',').filter(s => !!s) : []
  const keep = params ? params.drop_or_keep == 1 : true
  const oldKeep = oldParams ? oldParams.drop_or_keep == 1 : keep
  const keepIdx = keep ? 1 : 0
  const oldKeepIdx = oldKeep ? 1 : 0
  const colname = params.columnKey // may be undefined

  if (colnames.length === 0) {
    // Adding a new module, or resetting an empty one
    return { colnames: colname, drop_or_keep: keepIdx }
  } else {
    const idx = colnames.indexOf(colname)

    if (oldKeep) {
      // Existing module is "keep"
      if (keep) {
        throw new Error('Unhandled case: trying to keep in a keep module')
        return null
      } else {
        // We want to drop
        if (idx === -1) {
          return null // the keep module doesn't include colname: it's already dropped
        } else {
          colnames.splice(idx, 1)
          return { colnames: colnames.join(','), drop_or_keep: oldKeepIdx }
        }
      }
    } else {
      // Existing module is "drop"
      if (keep) {
        throw new Error('Unhandled case: trying to keep in a remove module')
        return null
      } else {
        // We want to drop another one
        if (idx === -1) {
          colnames.push(colname)
          return { colnames: colnames.join(','), drop_or_keep: oldKeepIdx }
        } else {
          return null // the drop module is already dropping colname
        }
      }
    }

    if (keep === oldKeep) {
      if (keep && idx === -1) {
        colnames.push(params.columnKey)
        return { colnames, drop_or_keep: keepIdx }
      } else if (!keep && idx !== -1) {
      } else {
        return null
      }
    } else {
      console.warn('Unimplemented drop/keep logic', oldKeep, keep, colnames, colname)
      return null
    }
  }
}

function buildEditCellsParams (oldParams, params) {
  const edits = (oldParams && oldParams.celledits) ? oldParams.celledits : []
  const edit = params

  // Remove the previous edit to the same cell
  const idx = edits.findIndex(({ row, col }) => row === edit.row && col === edit.col)

  if (idx === -1) {
    edits.push(edit)
    return { celledits: edits }
  } else if (edits[idx].value !== edit.value) {
    edits.splice(idx, 1, edit)
    return { celledits: edits }
  } else {
    return null
  }
}

function buildFilterParams (_oldParams, params) {
  return {
    filters: {
      operator: 'and',
      filters: [
        {
          operator: 'and',
          subfilters: [
            {
              colname: params.columnKey,
              condition: '',
              value: '',
              case_sensitive: false
            }
          ]
        }
      ]
    }
  }
}

function genericSetColumn (key) {
  return (oldParams, params) => {
    const newParams = { ...params }
    const colname = newParams.columnKey
    if (newParams.hasOwnProperty('columnKey')) {
      delete newParams.columnKey
      newParams[key] = colname
    }
    return newParamsUnlessNoChange(oldParams, newParams)
  }
}

function newParamsUnlessNoChange (oldParams, newParams) {
  if (!oldParams) return newParams
  for (const key in oldParams) {
    if (oldParams[key] !== newParams[key]) {
      return newParams
    }
  }
  return null
}

function genericAddColumn (key, deprecatedStringStorage) {
  return (oldParams, params) => {
    let colnames
    if (deprecatedStringStorage) {
      colnames = oldParams ? (oldParams[key] || '').split(',').filter(s => !!s) : []
    } else {
      colnames = oldParams ? (oldParams[key] || []) : []
    }
    if (!params.hasOwnProperty('columnKey'))  throw new Error('Expected "columnKey" column to add')
    const colname = params.columnKey

    if (!colname) throw new Error('Unexpected params: ' + JSON.stringify(params))

    if (colnames.includes(colname)) {
      return null
    } else {
      const newParams = { ...params }
      const colname = newParams.columnKey
      delete newParams.columnKey
      const newColnames = [ ...colnames, colname ]
      newParams[key] = deprecatedStringStorage ? newColnames.join(',') : newColnames

      return newParamsUnlessNoChange(oldParams, newParams)
    }
  }
}

function buildRenameColumnsParams (oldParams, params) {
  // renameInfo format: {prevName: <current column name in table>, newName: <new name>}
  const renames = oldParams && oldParams.renames || {}
  const { prevName, newName } = params

  if (renames[prevName] === newName) {
    return null
  } else {
    return {
      renames: {
        ...renames,
        [prevName]: newName
      }
    }
  }
}

function buildReorderColumnsParams (oldParams, params) {
  // Yes, yes, this is half-broken -- https://www.pivotaltracker.com/story/show/162592381
  const historyEntries = (oldParams && oldParams['reorder-history']) ? JSON.parse(oldParams['reorder-history']) : []

  let { column, to, from } = params

  // User must drag two spaces to indicate moving one column right (because drop = place before this column)
  // So to prevent all other code from having to deal with this forever, decrement the index here
  if (to > from) {
    to -= 1
  }

  historyEntries.push({ column, to, from })
  return { 'reorder-history': JSON.stringify(historyEntries) }
}

function buildSortColumnsParams (oldParams, params) {
  // 1. If the column is already the first param and directions the same, return null
  // 2. Remove existing column from param list, if it exists
  // 3. Prepend list with new column
  const newColumn = { colname: params.columnKey, is_ascending: params.is_ascending }

  if (oldParams == null) {
    return { sort_columns: [newColumn], keep_top: '' }
  }

  const columns = oldParams.sort_columns

  if (columns[0].colname === newColumn.colname && columns[0].is_ascending === newColumn.is_ascending) {
    return null
  }

  const sort_columns = columns.filter( column => column.colname !== params.columnKey)
  sort_columns.unshift(newColumn)

  const newParams = { sort_columns: sort_columns, keep_top: oldParams.keep_top }

  return newParams
}
