import {mockAPI, mockStore, deleteModuleAction, setSelectedWfModuleAction} from './workflow-reducer'

describe('Reducer actions', () => {

  var store, api;

  // Stripped down workflow object, only what we need for testing actions
  const test_workflow = {
    id: 999,
    wf_modules: [
      {
        id: 10
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

  // Stub result to be returned by our stub loadWorkflow
  const mock_load_workflow_result = { id: 1001 };

  // Mocks state and api globals in for this module
  beforeEach(() => {
    store = {
      getState: () => test_state,
      dispatch: jest.fn()
    };
    mockStore(store);

    api = {
      deleteModule: jest.fn().mockReturnValue(Promise.resolve()),   // api call returning nothing
      loadWorkflow: jest.fn().mockReturnValue(Promise.resolve(mock_load_workflow_result))
    };
    mockAPI(api);
  });

  // checks that removeModule() is called and selected module is not changed
  it('Remove non-selected module', (done) => {

    var actionPromise = deleteModuleAction(30);

    // Remove module should have been called
    expect(api.deleteModule.mock.calls.length).toBe(1);
    expect(api.deleteModule.mock.calls[0][0]).toBe(30);

    // actionPromise should eventually return reloadWorkflowAction(), which is a promise that resolves to reloaded wf
    actionPromise.then( result => {
      expect(result).toEqual({"type": "RELOAD_WORKFLOW", "workflow": mock_load_workflow_result});
    }).then( () => {
      done(); // need to tell jest that we are done with this async test
    });

  });

  // check that removing the selected module selects the one above it
  it('Remove selected module', (done) => {

    var actionPromise = deleteModuleAction(20); // 20 is selected module, in middle of stack

    // selected module should be set to previous, i.e. 10
    expect(store.dispatch.mock.calls.length).toBe(1);
    expect(store.dispatch.mock.calls[0][0]).toEqual(setSelectedWfModuleAction(10));

    // Remove module should have been called
    expect(api.deleteModule.mock.calls.length).toBe(1);
    expect(api.deleteModule.mock.calls[0][0]).toBe(20);

    // actionPromise should still resolve to a workflow reload
    actionPromise.then( result => {
      expect(result).toEqual({"type": "RELOAD_WORKFLOW", "workflow": mock_load_workflow_result});
    }).then( () => {
      done();
    });
  });

});




