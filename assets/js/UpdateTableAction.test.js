import { updateTableActionModule, selectColumnDrop, selectColumnKeep, updateModuleMapping } from './UpdateTableAction'
import {tick} from './test-utils'
import { store, addModuleAction, setParamValueAction, setParamValueActionByIdName, setSelectedWfModuleAction } from './workflow-reducer'

jest.mock('./workflow-reducer')

describe("UpdateTableAction actions", () => {
  // A few parameter id constants for better readability
  const idName = 'filter'
  const COLUMN_PAR_ID_1 = 35;

  var initialStateNone = {
    updateTableModuleIds: {'filter': null},
    workflow: {
      id: 127,
      wf_modules: [
        {
          id: 17,
          module_version: {
            module: {
              id_name: 'loadurl'
            }
          }
        }
      ]
    }
  }
  var initialState = {
    updateTableModuleIds: { 'filter': 77 },
    workflow: {
      id: 127,
      wf_modules: [
        {
          id: 17,
          module_version: {
            module: {
              id_name: 'loadurl'
            }
          }
        }
      ]
    }
  }

  // Change the module in the initial state
  function setInitialState (module) {
    initialState.updateTableModuleIds = module
    initialState.workflow.wf_modules[0].module_version.module.id_name = module
  }

  const addModuleResponse = {
    id: 23,
    module_version: {
      module: {
        id_name: idName
      }
    },
    parameter_vals: [
      {
        id: COLUMN_PAR_ID_1,
        parameter_spec: {id_name: 'column'},
        value: ''
      },
    ]
  };

  beforeEach(() => {
    store.getState.mockImplementation(() => initialState);
    // Our shim Redux API:
    // 1) actions are functions; dispatch returns their retvals in a Promise.
    //    This is useful when we care about retvals.
    // 2) actions are _not_ functions; dispatch does nothing. This is useful when
    //    we care about arguments.
    store.dispatch.mockImplementation(action => {
      if (typeof action === 'function') {
        return Promise.resolve({ value: action() })
      }
    });

    window.alert = jest.fn()

    for (var key in updateModuleMapping) {
      updateModuleMapping[key] = jest.fn()
    }

  })

  it('should call all functions per mapping', async () => {
    let params = {}
    for (let key in updateModuleMapping) {
      setInitialState(key)
      updateTableActionModule(17, key, false, params)
      await tick()
      expect(updateModuleMapping[key]).toHaveBeenCalled
    }
  })


  it('should alert user if module is not imported', async () => {
    store.getState.mockImplementation(() => initialStateNone)
    updateTableActionModule(17, 'filter', true, 'col_1')

    await tick();
    expect(window.alert).toHaveBeenCalledWith("Module 'filter' not imported.")
  });


});
