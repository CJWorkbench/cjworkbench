import { updateTableActionModule, selectColumnDrop, selectColumnKeep } from './UpdateTableAction'
import { tick } from './test-utils'
import { store, addModuleAction, setParamValueAction, setParamValueActionByIdName, setSelectedWfModuleAction } from './workflow-reducer'

jest.mock('./workflow-reducer');

describe("DropFromTable actions", () => {
  // A few parameter id constants for better readability
  const idName = 'selectcolumns'
  const COLUMN_PAR_ID_1 = 35;
  const COLUMN_PAR_ID_2 = 70;
  const COLUMN_PAR_ID_3 = 140;

  var initialState = {
    updateTableModuleIds: { 'selectcolumns': 77 },
    workflow: {
      id: 127,
      wf_modules: [ 17, 7, 19, 31, 79 ],
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
            id: COLUMN_PAR_ID_2,
            parameter_spec: {id_name: 'colnames'},
            value: 'col_1,col_2,col_3'
          },
          {
            id: COLUMN_PAR_ID_3,
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
            id: COLUMN_PAR_ID_3,
            parameter_spec: {id_name: 'colnames'},
            value: 'col_2,col_3'
          },
          {
            id: COLUMN_PAR_ID_3,
            parameter_spec: {id_name: 'drop_or_keep'},
            value: selectColumnDrop
          }
        ]
      }
    },
    modules: {
      77: { id_name: idName },
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
            id: COLUMN_PAR_ID_1,
            parameter_spec: {id_name: 'colnames'},
            value: ''
          },
          {
            id: COLUMN_PAR_ID_2,
            parameter_spec: {id_name: 'drop_or_keep'},
            value: ''
          }
        ]
      }
    }
  }

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

    setParamValueAction.mockImplementation((...args) => [ 'setParamValueAction', ...args ])
    setParamValueActionByIdName.mockImplementation((...args) => [ 'setParamValueActionByIdName', ...args ])
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  it('adds new select module after the given module and sets column parameter', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse);
    updateTableActionModule(19, idName, false, 'col_1');

    await tick();
    expect(addModuleAction).toHaveBeenCalledWith(77, 3);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 23, 'colnames', 'col_1' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 23, 'drop_or_keep', selectColumnDrop ]);
  });

  it('selects the existing select module. Removes column and sets action to keep', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, idName, false, 'col_2');

    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'colnames', 'col_1,col_3' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'drop_or_keep', selectColumnKeep ]);
  })

  it('selects the existing select module. Adds column and sets action to drop', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(31, idName, false, 'col_1');

    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 79, 'colnames', 'col_2,col_3,col_1' ]);
  })
});
