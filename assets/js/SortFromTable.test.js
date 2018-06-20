import { updateSort } from "./SortFromTable";
import { jsonResponseMock } from './test-utils'

jest.mock('./workflow-reducer')
import { store, addModuleAction, setParamValueAction, setParamValueActionByIdName, setSelectedWfModuleAction } from './workflow-reducer'

function tick() {
  return new Promise(resolve => {
    setTimeout(resolve, 0);
  })
}

describe("SortFromTable actions", () => {
  // A few parameter id constants for better readability
  const COLUMN_PAR_ID_1 = 35;
  const DTYPE_PAR_ID_1 = 85;
  const DIRECTION_PAR_ID_1 = 135;

  const COLUMN_PAR_ID_2 = 70;
  const DTYPE_PAR_ID_2 = 170;
  const DIRECTION_PAR_ID_2 = 270;

  const COLUMN_PAR_ID_3 = 140;
  const DTYPE_PAR_ID_3 = 340;
  const DIRECTION_PAR_ID_3 = 540;

  var initialState = {
    sortModuleId: 77,
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
        },
        {
          // An existing sort module
          id: 7,
          module_version: {
            module: {
              id_name: 'sort-from-table'
            }
          },
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
        {
          id: 19,
          module_version: {
            module: {
              id_name: 'colselect'
            }
          }
        },
        {
          id: 31,
          module_version: {
            module: {
              id_name: 'filter'
            }
          }
        },
        {
          // Another existing sort module, set to num_col descending
          id: 79,
          module_version: {
            module: {
              id_name: 'sort-from-table'
            }
          },
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
      ]
    }
  };

  const addModuleResponse = {
    id: 23,
    module_version: {
      module: {
        id_name: 'sort-from-table'
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
  };

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
    updateSort(19, 'num_col', 'Number');

    await tick();
    expect(addModuleAction).toHaveBeenCalledWith(initialState.sortModuleId, 3);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 23, 'column', 'num_col' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 23, 'dtype', 1 ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', DIRECTION_PAR_ID_1, 2 ]);
  });

  it('selects the existing sort module when updating it', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateSort(17, 'str_col', 'String');
    expect(store.dispatch).toHaveBeenCalledWith([ 'setSelectedWfModuleAction', 1 ]);
  })

  it('orders a String column ascending by default', async () => {
    // Click on 'str_col' once, which should give us ascending order
    updateSort(17, 'str_col', 'String');
    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'column', 'str_col' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 7, 'dtype', 0 ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', DIRECTION_PAR_ID_2, 1 ]);
  });

  it('orders a Number column descending by default', async () => {
    updateSort(17, 'num_col', 'Number');
    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', DIRECTION_PAR_ID_2, 2 ]);
  });

  it('orders a Data column descending by default', async () => {
    updateSort(17, 'date_col', 'Date');
    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', DIRECTION_PAR_ID_2, 2 ]);
  });

  it('resets ordering state when changing sort column', async () => {
    // sort 79 is for 'num_col' in initial state. Change to 'str_col' and expect ascending order
    updateSort(79, 'str_col', 'String');
    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 79, 'column', 'str_col' ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueActionByIdName', 79, 'dtype', 0 ]);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', DIRECTION_PAR_ID_2, 1 ]);
  });
});
