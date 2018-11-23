import { updateTableActionModule } from './UpdateTableAction'
import { tick } from '../test-utils'
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe('DuplicateFromTable actions', () => {
  // A few parameter id constants for better readability
  const initialState = {
    workflow: {
      id: 127,
      wf_modules: [ 17, 7, 19, 31, 79 ]
    },
    modules: {
      1: { id_name: 'loadurl' },
      2: { id_name: 'colselect' },
      3: { id_name: 'filter' },
      77: { id_name: 'duplicate-column' }
    },
    wfModules: {
      17: { module_version: { module: 1 } },
      7: {
        // An existing duplicate module
        id: 7,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: 'col_1'
          }
        ]
      },
      19: { module_version: { module: 2 } },
      31: { module_version: { module: 3 } },
      79: {
        // Another existing duplicate module, set existing duplicates col_2,col_3
        id: 79,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: 'col_2,col_3'
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

  it('adds new duplicate module after the given module and sets column parameter', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(19, 'duplicate-column', false, { columnKey: 'col_1' })

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('duplicate-column', 3)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 23, { colnames: 'col_1' }])
  })

  it('selects the existing duplicate module and adds a new column to duplicate', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, 'duplicate-column', false, { columnKey: 'col_2' })

    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 7, { colnames: 'col_1,col_2' }])
  })

  it('selects the existing duplicate module and tries to duplicate the same column', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, 'duplicate-column', false, { columnKey: 'col_1' })

    // Sets selected module (no change)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setSelectedWfModuleAction', 1 ])
    expect(store.dispatch).toHaveBeenCalledTimes(1)
  })
})
