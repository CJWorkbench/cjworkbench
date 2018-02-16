import {addCellEdit, mockAPI } from "./EditCells";
import {mockStore} from './workflow-reducer'
import { jsonResponseMock } from './utils'

describe('Edit Cell actions', () => {

  var store, api;

  // Stripped down workflow object, only what we need for testing cell editing
  const test_workflow = {
    id: 999,
    wf_modules: [
      {
        id: 10,
        module_version : {
          module: {
            id_name: 'loadurl'
          }
        }
      },
      {
        // Existing Edit Cells module with existing edits
        id: 20,
        module_version : {
          module : {
            id_name: 'editcells'
          }
        },
        parameter_vals: [
          {
            id: 101,
            parameter_spec: { id_name: 'celledits' },
            value: '[{ "row":3, "col":"foo", "value":"bar" }]'
          }
        ]
      },
      {
        id: 30,
        module_version : {
          module: {
            id_name: 'filter'
          }
        }
      },
      {
        id: 40,
        module_version : {
          module: {
            id_name: 'dropna'
          }
        }
      },
    ],
  };

  // mocked data from api.addModule call, looks like a just-added edit cells module
  const addModuleReponse = {
    id: 99,
    module_version : {
      module : {
        id_name: 'editcells'
      }
    },
    parameter_vals: [
      {
        id: 999,
        parameter_spec: { id_name: 'celledits' },
        value: ''
      }
    ]
  };

  const initialState = {
    workflow: test_workflow,
    editCellsModuleId: 5000
  };

  // Mocks store and api
  beforeEach(() => {
    api = {
      onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
      addModule: jsonResponseMock(addModuleReponse)
    };
    mockAPI(api);

    store = {
      getState: () => initialState,
      dispatch: jest.fn()
    };
    mockStore(store);
  });


  it('Add edit to existing Edit Cell module', () => {
      addCellEdit(20, {row: 10, col:'bar', 'value':'yippee!'});

      expect(api.onParamChanged.mock.calls).toHaveLength(1);
      expect(api.onParamChanged.mock.calls[0][0]).toBe(101);
      expect(api.onParamChanged.mock.calls[0][1]).toEqual(
        { value: '[{"row":3,"col":"foo","value":"bar"},{"row":10,"col":"bar","value":"yippee!"}]' } );
  });

    it('Add edit to immediately following Edit Cell module', () => {
      addCellEdit(10, {row: 10, col:'bar', 'value':'yippee!'});

      expect(api.onParamChanged.mock.calls).toHaveLength(1);
      expect(api.onParamChanged.mock.calls[0][0]).toBe(101);
      expect(api.onParamChanged.mock.calls[0][1]).toEqual(
        { value: '[{"row":3,"col":"foo","value":"bar"},{"row":10,"col":"bar","value":"yippee!"}]' } );
  });

  it('Add new Edit Cells module before end of stack', (done) => {
      addCellEdit(30, {row: 10, col:'bar', 'value':'yippee!'});

      expect(api.addModule.mock.calls).toHaveLength(1);
      expect(api.addModule.mock.calls[0][1]).toEqual(initialState.editCellsModuleId);
      expect(api.addModule.mock.calls[0][2]).toEqual(3); // insert before this module

      // let addModule promise resolve
      setImmediate( () => {
        expect(api.onParamChanged.mock.calls).toHaveLength(1);
        expect(api.onParamChanged.mock.calls[0][0]).toBe(999);
        expect(api.onParamChanged.mock.calls[0][1]).toEqual(
           { value: '[{"row":10,"col":"bar","value":"yippee!"}]' } );
        done();
      })
  });

  it('Add new Edit Cells module at end of stack', (done) => {
      addCellEdit(40, {row: 10, col:'bar', 'value':'yippee!'});

      expect(api.addModule.mock.calls).toHaveLength(1);
      expect(api.addModule.mock.calls[0][1]).toEqual(initialState.editCellsModuleId);
      expect(api.addModule.mock.calls[0][2]).toEqual(4); // insert before this module == end of stack

      // let addModule promise resolve
      setImmediate( () => {
        expect(api.onParamChanged.mock.calls).toHaveLength(1);
        expect(api.onParamChanged.mock.calls[0][0]).toBe(999);
        expect(api.onParamChanged.mock.calls[0][1]).toEqual(
           { value: '[{"row":10,"col":"bar","value":"yippee!"}]' } );
        done();
      })
  });

});




