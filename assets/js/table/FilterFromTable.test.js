import { updateTableActionModule, selectColumnDrop, selectColumnKeep } from './UpdateTableAction'
import { tick } from '../test-utils'
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe("FilterFromTable actions", () => {
  // A few parameter id constants for better readability
  const initialState = {
    workflow: {
      id: 127,
      tab_ids: [ 10, 11 ],
      selected_tab_position: 1
    },
    tabs: {
      11: { wf_module_ids: [ 17, 19, 7, 19, 31 ] }
    },
    modules: {
      77: { id_name: 'filter' },
      1: { id_name: 'loadurl' },
      2: { id_name: 'selectcolumns' }
    },
    wfModules: {
      17: { module_version: { module: 1 } },
      18: { module_version: { module: 2 } },
      7: {
        // An existing select module with 2 columns kept
        id: 7,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'column'},
            value: 'col_1'
          }
        ]
      },
      19: { module_version: { module: 2 } },
      31: { module_version: { module: 2 } }
    }
  }

  const addModuleResponse = {
    data: {
      wfModule: {
        id: 23,
        module_version: {
          module: {
            id_name: 'filter'
          }
        },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'column'},
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

  it('adds new filter module after the given module and sets column parameter', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(17, 'filter', true, { columnKey: 'col_1' })

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('filter', { tabId: 11, index: 1 })
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 23, { column: 'col_1'} ])
  })

  it('selects the existing filter module but forces add new', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(7, 'filter', true, { columnKey: 'col_2' })

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('filter', { tabId: 11, index: 3 })
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 23, { column: 'col_2' }])
  })
})
