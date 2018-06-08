import * as wfr from './workflow-reducer'
import { jsonResponseMock, genericTestModules } from './test-utils'

const workflowReducer = wfr.workflowReducer;

// Sets a specfic function for reduver mockAPI, with optional json return
function installMockApiCall(key, response) {
  let mockFn = response ? jsonResponseMock(response) : jest.fn();
  const api = {
    [key] : mockFn
  };
  wfr.mockAPI(api);
  return api;
}

describe('Reducer actions', () => {

  // Stripped down workflow object, only what we need for testing actions
  const test_workflow = {
    id: 999,
    selected_wf_module: 30,  // different than test_state.selected_wf_module so we can test setting state.selected_wf_module
    wf_modules: [
      {
        id: 10,
        parameter_vals: [
          {
            id: 1,
            parameter_spec : {
              id_name: 'data',
            },
            value: 'Some Data'
          }
        ],
        versions: {
          selected: "2018-02-21T03:09:20.214054Z",
          versions: [
            ["2018-02-21T03:09:20.214054Z", true],
            ["2018-02-21T03:09:15.214054Z", false],
            ["2018-02-21T03:09:10.214054Z", false]
          ]
        },
        notification_count: 2
      },
      {
        id: 20
      },
      {
        id: 30
      },
    ],
  };

  // test state has second module selected
  const test_state = {
    workflow: test_workflow,
    selected_wf_module: 20
  };

  // many action creators reference the current store
  wfr.mockStore({
    getState : () => test_state
  });

  // Stub result to be returned by our stub loadWorkflow
  //const mock_load_workflow_result = { id: 1001 };
  const mock_add_wf_module_result = { id: 40, insert_before: 2 };

  it('Returns the state if we feed garbage to the reducer', () => {
    const state = workflowReducer(test_state, {
      type: 'An ill-advised request',
      payload: {
        blob: 'malware.exe'
      }
    });
    expect(state).toBe(test_state);
  });

  // RELOAD_WORKFLOW
   it('Reloads the workflow', () => {
    const state = workflowReducer(test_state, {
      type: 'RELOAD_WORKFLOW_FULFILLED',
      payload: test_workflow,
    });
    expect(state.workflow).toEqual(test_workflow);
    expect(state.selected_wf_module).toEqual(test_workflow.selected_wf_module);
  });

   // LOAD_MODULES
   it('loadModules', () => {
     let api = installMockApiCall('getModules', genericTestModules);
     let action = wfr.loadModulesAction();
     expect(api.getModules).toHaveBeenCalled();

    const state = workflowReducer(test_state, {
      type: 'LOAD_MODULES_FULFILLED',
      payload: genericTestModules
    });
    expect(state.modules).toEqual(genericTestModules);
  });

  // ADD_MODULE
  it('Adds a module', () => {
    const state = workflowReducer(test_state, {
      type: 'ADD_MODULE_FULFILLED',
      payload: mock_add_wf_module_result,
    });
    expect(state.workflow.wf_modules[2].id).toEqual(40);
    expect(state.selected_wf_module).toEqual(40);
  });

  it('Deletes a module', () => {
    const state = workflowReducer(test_state, {
      type: 'DELETE_MODULE_PENDING',
      payload: {
        wf_module_id: 20
      }
    });
    expect(state.workflow.wf_modules.length).toEqual(2);
  });

  it('Sets the selected module to a module in state', () => {
    const state = workflowReducer(test_state, {
     type: 'SET_SELECTED_MODULE_PENDING',
     payload: {
       wf_module_id: 30
     }
    });
    expect(state.selected_wf_module).toBe(30);
  });

  it('Updates the workflow module with the specified data', () => {
    const state = workflowReducer(test_state, {
      type: 'UPDATE_WF_MODULE_PENDING',
      payload: {
        id: 20,
        data: {
          notifications: true
        }
      }
    });
    expect(state.workflow.wf_modules[1].notifications).toBe(true);
  });

  it('Returns the state if we update a nonexistent wfmodule', () => {
    const state = workflowReducer(test_state, {
      type: 'UPDATE_WF_MODULE_PENDING',
      payload: {
        id: 40,
        data: {
          notifications: true
        }
      }
    });
    expect(state).toBe(test_state);
  });

  it('Sets the wfModule status', () => {
    const state = workflowReducer(test_state, {
      type: 'SET_WF_MODULE_STATUS',
      payload: {
        id: 20,
        status: 'error',
        error_msg: 'There was an error'
      }
    });

    expect(state.workflow.wf_modules[1].status).toBe('error');

    const state2 = workflowReducer(state, {
      type: 'SET_WF_MODULE_STATUS',
      payload: {
        id: 20,
        status: 'error',
        error_msg: 'There was another error'
      }
    });

    expect(state2.workflow.wf_modules[1].error_msg).toBe('There was another error');
  });

  it('Sets the module collapse state', () => {
    const state = workflowReducer(test_state, {
      type: 'SET_WF_MODULE_COLLAPSED_PENDING',
      payload: {
        wf_module_id: 20,
        is_collapsed: true
      }
    });
    expect(state.workflow.wf_modules[1].is_collapsed).toBe(true);
  });

  it('setParamValueAction', () => {
    const api = {
      onParamChanged : jest.fn()
    };
    wfr.mockAPI(api);

    const paramId = test_workflow.wf_modules[0].parameter_vals[0].id;
    let action = wfr.setParamValueAction(paramId, {value:'foo'});
    expect(action.payload.data.paramId).toBe(paramId);
    expect(action.payload.data.paramValue).toBe('foo');
    expect(api.onParamChanged.mock.calls.length).toBe(1);  // should have called the api

    // If we create an action to set the parameter to the existing value, nothing should happen...
    api.onParamChanged = jest.fn();
    const curParamVal = test_workflow.wf_modules[0].parameter_vals[0].value;
    action = wfr.setParamValueAction(paramId, {value:curParamVal});
    expect(action.type).toBe(wfr.NOP_ACTION);
    expect(api.onParamChanged.mock.calls.length).toBe(0);

    // Version that takes moduleId and id_name
    api.onParamChanged = jest.fn();
    const moduleId = test_workflow.wf_modules[0].id;
    const idName = test_workflow.wf_modules[0].parameter_vals[0].parameter_spec.id_name;
    action = wfr.setParamValueActionByIdName(moduleId, idName, {value:'foo'});
    expect(action.payload.data.paramId).toBe(paramId);
    expect(action.payload.data.paramValue).toBe('foo');
    expect(api.onParamChanged.mock.calls.length).toBe(1);  // should have called the api
  });


  it('Sets the param value', () => {
    const state = workflowReducer(test_state, {
      type: 'SET_PARAM_VALUE_PENDING',
      payload: {
        paramId: 1,
        paramValue: "Other data",
      }
    });
    expect(state.workflow.wf_modules[0].parameter_vals[0].value).toBe("Other data");
  });

  it('Sets the data version', () => {
    const state = workflowReducer(test_state, {
      type: 'SET_DATA_VERSION_PENDING',
      payload: {
        wfModuleId: 10,
        selectedVersion: "2018-02-21T03:09:10.214054Z"
      }
    });
    expect(state.workflow.wf_modules[0].versions.selected).toBe("2018-02-21T03:09:10.214054Z");
  });

  it('Marks the data versions read', () => {
    const state = workflowReducer(test_state, {
      type: 'MARK_DATA_VERSIONS_READ_PENDING',
      payload: {
        id: 10,
        versions_to_update: ["2018-02-21T03:09:15.214054Z", "2018-02-21T03:09:10.214054Z"]
      }
    });
    expect(state.workflow.wf_modules[0].versions.versions[1][1]).toBe(true);
    expect(state.workflow.wf_modules[0].versions.versions[2][1]).toBe(true);
  });

  it('Clears the notification count', () => {
    const state = workflowReducer(test_state, {
      type: 'CLEAR_NOTIFICATIONS_PENDING',
      payload: {
        wfModuleId: 10
      }
    });
    expect(state.workflow.wf_modules[0].notification_count).toBe(0);
  });
});
