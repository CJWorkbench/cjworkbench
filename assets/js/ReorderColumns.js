import {store} from './workflow-reducer';
import {findModuleWithIdAndIdName, findParamValByIdName, getWfModuleIndexfromId, DEPRECATED_ensureSelectedWfModule} from './utils';
import WorkbenchAPI from './WorkbenchAPI';

var api = WorkbenchAPI()
export function mockAPI(mockAPI) {
  api = mockAPI
}

function updateReorderModule(module, reorderInfo) {
  var historyParam = findParamValByIdName(module, 'reorder-history')
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
  api.onParamChanged(historyParam.id, {value: JSON.stringify(historyEntries)})
}

export function updateReorder(wfModuleId, reorderInfo) {
  const state = store.getState()
  const workflowId = state.workflow ? state.workflow.id : null

  const existingReorderModule = findModuleWithIdAndIdName(state, wfModuleId, 'reorder-columns')
  if (existingReorderModule) {
    updateReorderModule(existingReorderModule, reorderInfo)
    DEPRECATED_ensureSelectedWfModule(store, existingReorderModule)
  } else {
    const wfModuleIdx = getWfModuleIndexfromId(state, wfModuleId)
    api.addModule(workflowId, state.reorderModuleId, wfModuleIdx + 1)
      .then((newWfm) => {
        updateReorderModule(newWfm, reorderInfo)
        DEPRECATED_ensureSelectedWfModule(store, newWfm)
      })
  }
}
