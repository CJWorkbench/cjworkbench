import { updateTableActionModule } from './UpdateTableAction'
import {tick} from "./test-utils"

jest.mock('./workflow-reducer');
import { store, addModuleAction, setParamValueAction, setSelectedWfModuleAction } from './workflow-reducer'


describe('RenameColumns actions', () => {
  // A few parameter id constants for readability
  const idName = 'rename-columns'

  const LOADURL_WFM_ID = 35;

  const FILTER_WFM_ID = 50;

  const RENAME_WFM_ID = 85;
  const RENAME_ENTRIES_ID = 105;

  const NEW_RENAME_WFM_ID = 120;
  const NEW_RENAME_ENTRIES_ID = 150;

  const RENAME_MODULE_ID = 24;
  const WF_ID = 18;

  var initialState = {
    updateTableModuleIds: { 'rename-columns': RENAME_MODULE_ID },
    workflow: {
      id: WF_ID,
      wf_modules: [
        {
          id: LOADURL_WFM_ID,
          module_version: {
            module: {
              id_name: 'loadurl'
            }
          }
        },
        {
          id: FILTER_WFM_ID,
          module_version: {
            module: {
              id_name: 'filter'
            }
          }
        },
        {
          id: RENAME_WFM_ID,
          module_version: {
            module: {
              id_name: idName
            }
          },
          parameter_vals: [
            {
              id: RENAME_ENTRIES_ID,
              parameter_spec: {
                id_name: 'rename-entries'
              },
              value: JSON.stringify({
                'name': 'host_name',
                'narrative': 'nrtv'
              })
            }
          ]
        }
      ]
    }
  };

  const addModuleResponse = {
    id: NEW_RENAME_WFM_ID,
    module_version: {
      module: {
        id_name: idName
      }
    },
    parameter_vals: [
      {
        id: NEW_RENAME_ENTRIES_ID,
        parameter_spec: {
          id_name: 'rename-entries'
        },
        value: ''
      }
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

    setParamValueAction.mockImplementation((...args) => [ 'setParamValueAction', ...args ])
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  it('adds a new rename module after the current non-rename module', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse);
    updateTableActionModule(LOADURL_WFM_ID, idName, { prevName: 'cornerstone', newName: 'cs' })

    await tick();
    expect(addModuleAction).toHaveBeenCalledWith(initialState.updateTableModuleIds[idName], 1);
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', NEW_RENAME_ENTRIES_ID, JSON.stringify({ cornerstone: 'cs' }) ]);
  });

  it('adds a new column to an existing rename module', async () => {
    updateTableActionModule(FILTER_WFM_ID, idName, { prevName: 'cornerstone', newName: 'cs' })

    await tick();
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', RENAME_ENTRIES_ID, JSON.stringify({ name: 'host_name', narrative: 'nrtv', cornerstone: 'cs' }) ]);
  });

  it('renames an already-renamed column', async () => {
    updateTableActionModule(FILTER_WFM_ID, idName, { prevName: 'host_name', newName: 'host' })

    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', RENAME_ENTRIES_ID, JSON.stringify({ name: 'host', narrative: 'nrtv' }) ]);
  });
});
