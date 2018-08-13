import { sortDirectionAsc, sortDirectionDesc, sortDirectionNone, updateTableActionModule } from './UpdateTableAction'
import {tick} from './test-utils'
import { store, addModuleAction, setParamValueAction, setParamValueActionByIdName, setSelectedWfModuleAction } from './workflow-reducer'

jest.mock('./workflow-reducer');

describe("SortFromTable actions", () => {
  // A few parameter id constants for better readability
  const idName = 'sort-from-table'
  const COLUMN_PAR_ID_1 = 35;
  const DTYPE_PAR_ID_1 = 85;
  const DIRECTION_PAR_ID_1 = 135;

  const COLUMN_PAR_ID_2 = 70;
  const DTYPE_PAR_ID_2 = 170;
  const DIRECTION_PAR_ID_2 = 270;

  const COLUMN_PAR_ID_3 = 140;
  const DTYPE_PAR_ID_3 = 340;
  const DIRECTION_PAR_ID_3 = 540;

  const initialState = {
    updateTableModuleIds: { 'sort-from-table': 77 },
    workflow: {
      id: 127,
      wf_modules: [ 17, 7, 19, 31, 79 ]
    },
    modules: {
      1: { id_name: 'loadurl' },
      2: { id_name: 'filter' },
      77: { id_name: 'sort-from-table' }
    },
    wfModules: {
      17: { id: 17, module_version: { module: 1 } },
      7: {
        // An existing sort module
        id: 7,
        module_version: { module: 77 },
        parameter_vals: [
          {
            id: COLUMN_PAR_ID_2,
            parameter_spec: {id_name: 'column'},
            value: ''
          },
          {
            id: DTYPE_PAR_ID_2,
            parameter_spec: {id_name: 'dtype'},
            value: 0   // String
          },
          {
            id: DIRECTION_PAR_ID_2,
            parameter_spec: {id_name: 'direction'},
            value: 0     // Select
          }
        ]
      },
      19: { module_version: { module: 2 } },
      31: { module_version: { module: 2 } },
      79: {
        // Another existing sort module, set to num_col descending
        id: 79,
        module_version: { module: 77 },
        parameter_vals: [
          {
            id: COLUMN_PAR_ID_3,
            parameter_spec: {id_name: 'column'},
            value: 'num_col'
          },
          {
            id: DTYPE_PAR_ID_3,
            parameter_spec: {id_name: 'dtype'},
            value: 1   // Number
          },
          {
            id: DIRECTION_PAR_ID_3,
            parameter_spec: {id_name: 'direction'},
            value: 2   // Descending
          }
        ]
      }
    }
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
            parameter_spec: {id_name: 'column'},
            value: ''
          },
          {
            id: DTYPE_PAR_ID_1,
            parameter_spec: {id_name: 'dtype'},
            value: 0,
          },
          {
            id: DIRECTION_PAR_ID_1,
            parameter_spec: {id_name: 'direction'},
            value: 0
          }
        ]
      }
    }
  }

  const columnsResponse = [
    {name: "num_col", type: "Number"},
    {name: "str_col", type: "String"},
    {name: "date_col", type: "Date"},
  ];

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

  it('adds new sort module after the given module and sets sort parameters', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse);
    updateTableActionModule(19, idName, false, {columnKey: 'num_col', sortType: 'number', sortDirection: sortDirectionNone});

    await tick();
    expect(addModuleAction).toHaveBeenCalledWith(initialState.updateTableModuleIds[idName], 3);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 23, 'column', 'num_col' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 23, 'dtype', 1 ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 23, 'direction', sortDirectionNone ]);
    //expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', DIRECTION_PAR_ID_1, 2 ]);
  });

  it('selects the existing sort module when updating it', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, idName, false, {columnKey: 'str_col', columnType: 'text'});

    expect(store.dispatch).toHaveBeenCalledWith([ 'setSelectedWfModuleAction', 1 ]);
  })

  it('orders a String column ascending by default', async () => {
    // Click on 'str_col' once, which should give us ascending order
    updateTableActionModule(17, idName, false, {columnKey: 'str_col', sortType: 'text', sortDirection: sortDirectionAsc});

    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'column', 'str_col' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'dtype', 0 ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'direction', sortDirectionAsc ]);
  });

  it('orders a Number column descending by default', async () => {
    updateTableActionModule(17, idName, false, {columnKey: 'num_col', sortType: 'number', sortDirection: sortDirectionDesc});

    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'direction', sortDirectionDesc ]);
  });

  it('orders a Data column descending by default', async () => {
    updateTableActionModule(17, idName, false, {columnKey: 'date_col', sortType: 'datetime', sortDirection: sortDirectionDesc});

    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'direction', sortDirectionDesc ]);
  });

  it('resets ordering state when changing sort column', async () => {
    // sort 79 is for 'num_col' in initial state. Change to 'str_col' and expect ascending order
    updateTableActionModule(79, idName, false, {columnKey: 'str_col', sortType: 'text', sortDirection: sortDirectionAsc});

    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 79, 'column', 'str_col' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 79, 'dtype', 0 ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 79, 'direction', sortDirectionAsc ]);
  });
});
