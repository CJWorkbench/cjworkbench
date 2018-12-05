import { updateTableActionModule, selectColumnDrop, selectColumnKeep } from './UpdateTableAction'
import { tick } from '../test-utils'
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe("DropFromTable actions", () => {
  const initialState = {
    workflow: {
      tab_ids: [ 10, 11 ],
      selected_tab_position: 1
    },
    tabs: {
      11: { wf_module_ids: [ 17, 7, 19, 31, 79 ] }
    },
    wfModules: {
      17: {
        id: 17,
        module_version: { module: 4 }
      },
      7: {
        // An existing select module with 2 columns kept
        id: 7,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: 'col_1,col_2,col_3'
          },
          {
            parameter_spec: {id_name: 'drop_or_keep'},
            value: selectColumnKeep
          }
        ]
      },
      19: {
        id: 19,
        module_version: { module: 2 }
      },
      31: {
        id: 31,
        module_version: { module: 3 }
      },
      79: {
        // Another existing select module, set existing drops of col_2,col_3
        id: 79,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: 'col_2,col_3'
          },
          {
            parameter_spec: {id_name: 'drop_or_keep'},
            value: selectColumnDrop
          }
        ]
      }
    },
    modules: {
      77: { id_name: 'selectcolumns' },
      2: { id_name: 'colselect' },
      3: { id_name: 'filter' },
      4: { id_name: 'loadurl' }
    }
  }

  const addModuleResponse = {
    data: {
      index: 1,
      wfModule: {
        id: 23,
        module_version: { module: 1 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: ''
          },
          {
            parameter_spec: {id_name: 'drop_or_keep'},
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
    store.dispatch.mockImplementation(action => {
      if (typeof action === 'function') {
        return Promise.resolve({ value: action() })
      }
    })

    setWfModuleParamsAction.mockImplementation((...args) => [ 'setWfModuleParamsAction', ...args ])
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  it('adds new select module after the given module and sets column parameter', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(19, 'selectcolumns', false, {columnKey: 'col_1'})

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('selectcolumns', { tabId: 11, index: 3 })
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 23, { colnames: 'col_1', 'drop_or_keep': selectColumnDrop }])
  })

  it('selects the existing select module. Removes column and sets action to keep', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, 'selectcolumns', false, {columnKey: 'col_2'})

    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 7, { colnames: 'col_1,col_3', 'drop_or_keep': selectColumnKeep }])
  })

  it('selects the existing select module. Adds column and sets action to drop; FIXME this test does not match its description', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(31, 'selectcolumns', false, {columnKey: 'col_1'})

    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 79, { colnames: 'col_2,col_3,col_1' } ])
  })
})
