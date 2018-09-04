import { updateTableActionModule, selectColumnDrop, selectColumnKeep, updateModuleMapping } from './UpdateTableAction'
import { tick } from '../test-utils'
// TODO do not import store
import { store, addModuleAction, setParamValueAction, setParamValueActionByIdName, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe("UpdateTableAction actions", () => {
  // A few parameter id constants for better readability
  const idName = 'filter'
  const COLUMN_PAR_ID_1 = 35

  const initialState = {
    updateTableModuleIds: { 'filter': 77 },
    workflow: {
      id: 127,
      wf_modules: [ 17 ]
    },
    wfModules: {
      17: { module_version: { module: 1 } }
    },
    modules: {
      1: { id_name: 'loadurl' }
    }
  }

  const forceNewModules = ['filter']

  // Change the module in the initial state
  function setInitialState (module) {
    initialState.updateTableModuleIds = { module: 666 }
    initialState.workflow.wf_modules[0].module_version.module.id_name = module
  }

  const addModuleResponse = {
    data: {
      wfModule: {
        id: 23,
        module_version: {
          module: {
            id_name: idName
          }
        },
        parameter_vals: [
          {
            id: COLUMN_PAR_ID_1,
            parameter_spec: { id_name: 'column' },
            value: ''
          }
        ]
      }
    }
  }

  function initStore (moduleIdName) {
    store = mockStore({ ...initialState,
      modules: { 1: { id_name: moduleIdName } }
    })

    // Our shim Redux API:
    // 1) actions are functions; dispatch returns their retvals in a Promise.
    //    This is useful when we care about retvals.
    // 2) actions are _not_ functions; dispatch does nothing. This is useful when
    //    we care about arguments.
    window.alert = jest.fn()

    for (let key in updateModuleMapping) {
      updateModuleMapping[key] = jest.fn()
    }
  }

  beforeEach(() => {
    // Our shim Redux API:
    // 1) actions are functions; dispatch returns their retvals in a Promise.
    //    This is useful when we care about retvals.
    // 2) actions are _not_ functions; dispatch does nothing. This is useful when
    //    we care about arguments.
    store.dispatch.mockImplementation(action => {
      if (typeof action === 'function') {
        return Promise.resolve({ value: action() })
      } else {
        return Promise.resolve(null)
      }
    })

    for (let key in updateModuleMapping) {
      updateModuleMapping[key] = jest.fn()
    }
  })

  let _alert
  beforeEach(() => {
    _alert = window.alert
    window.alert = jest.fn()
  })
  afterEach(() => {
    window.alert = _alert
  })

  for (let moduleIdName in updateModuleMapping) {
    it(`should call ${moduleIdName} per mapping`, async () => {
      const addModuleResponse = {data: {wfModule: {id: 18}}};
      addModuleAction.mockImplementation(() => () => addModuleResponse);
      // TODO use mockStore, not store
      store.getState.mockImplementation(() => ({
        ...initialState,
        updateModuleMapping: { [moduleIdName]: 77 },
        modules: { 77: { id_name: moduleIdName } }
      }))

      if (forceNewModules.includes(moduleIdName)) {
        updateTableActionModule(17, moduleIdName, true, {})
      }
      else {
        updateTableActionModule(17, moduleIdName, false, {})
      }
      await tick()
      expect(updateModuleMapping[moduleIdName]).toHaveBeenCalled
    })
  }

  it('should alert user if module is not imported', async () => {
    const initialStateNone = {
      updateTableModuleIds: {},  // no modules installed, error condition if unchanged
      workflow: {
        id: 127,
        wf_modules: [ 17 ]
      },
      wfModules: {
        17: { module_version: { module: 1 } },
      },
      modules: {
        1: { id_name: 'loadurl' }
      }
    }
    store.getState.mockImplementation(() => initialStateNone)
    updateTableActionModule(17, 'filter', true, 'col_1')

    await tick()
    expect(window.alert).toHaveBeenCalledWith("Module 'filter' not imported.")
  })
})
