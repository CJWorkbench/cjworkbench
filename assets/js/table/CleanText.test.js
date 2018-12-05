import { updateTableActionModule } from './UpdateTableAction'
import { tick } from '../test-utils'
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe("CleanText actions", () => {
  const initialState = {
    workflow: {
      id: 127,
      tab_ids: [ 10, 11 ],
      selected_tab_position: 1
    },
    tabs: {
      11: { wf_module_ids: [ 17, 7, 19, 31, 79 ] }
    },
    modules: {
      1: { id_name: 'loadurl' },
      2: { id_name: 'filter' },
      77: { id_name: 'clean-text' }
    },
    wfModules: {
      17: { id: 17, module_version: { module: 1 } },
      7: {
        // An existing extract module
        id: 7,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: { id_name: 'colnames' },
            value: 'num_col'
          }
        ]
      },
      19: { module_version: { module: 2 } },
      31: { module_version: { module: 2 } },
      79: {
        // Another existing extract module, set to Int type
        id: 79,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: { id_name: 'colnames' },
            value: 'num_col'
          }
        ]
      }
    }
  }

  const addModuleResponse = {
    data: {
      index: 2,
      wfModule: {
        id: 23,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: { id_name: 'colnames' },
            value: ''
          }
        ]
      }
    }
  }

  beforeEach(() => {
    store.getState.mockReset()
    store.getState.mockImplementation(() => initialState)
    // Our shim Redux API:
    // 1) actions are functions; dispatch returns their retvals in a Promise.
    //    This is useful when we care about retvals.
    // 2) actions are _not_ functions; dispatch does nothing. This is useful when
    //    we care about arguments.
    store.dispatch.mockReset()
    store.dispatch.mockImplementation(action => {
      if (typeof action === 'function') {
        return Promise.resolve({ value: action() })
      }
    })

    setWfModuleParamsAction.mockReset()
    setWfModuleParamsAction.mockImplementation((...args) => [ 'setWfModuleParamsAction', ...args ])
    setSelectedWfModuleAction.mockReset()
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  it('adds new module after the given module and set "colnames"', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(19, 'clean-text', false, {columnKey: 'num_col'})

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('clean-text', { tabId: 11, index: 3 })
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 23, { colnames: 'num_col' }])
  })

  it('selects the existing extract module with same column and does nothing', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, 'clean-text', false, {columnKey: 'num_col'})

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith(['setSelectedWfModuleAction', 1])
  })

  it('should force a new module when an existing one has the before flag set', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(79, 'clean-text', false, {columnKey: 'str_col'})

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('clean-text', { tabId: 11, index: 5 })
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 23, { colnames: 'str_col' } ])
  })
})
