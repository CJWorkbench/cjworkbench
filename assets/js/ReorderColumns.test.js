import {updateReorder, mockAPI} from "./ReorderColumns";
import {mockStore, mockAPI as mockStoreApi} from "./workflow-reducer";
import {jsonResponseMock} from "./test-utils";

describe('ReorderColumns actions', () => {
    var store, api;

    // A few parameter id constants for better readability
    const LOADURL_WFM_ID = 35;

    const FILTER_WFM_ID = 50;

    const REORDER_WFM_ID = 85;
    const REORDER_HISTORY_PAR_ID = 90;

    const NEW_REORDER_WFM_ID = 135;
    const NEW_REORDER_HISTORY_PAR_ID = 105;

    const REORDER_MODULE_ID = 24;
    const WF_ID = 10;

    var initialState = {
        reorderModuleId: REORDER_MODULE_ID,
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
                    id: REORDER_WFM_ID,
                    module_version: {
                        module: {
                            id_name: 'reorder-columns'
                        },
                    },
                    parameter_vals: [
                        {
                            id: REORDER_HISTORY_PAR_ID,
                            parameter_spec: {
                                id_name: 'reorder-history'
                            },
                            value: ''
                        }
                    ]
                }
            ]
        }
    };

    const addModuleResponse = {
        id: NEW_REORDER_WFM_ID,
        module_version: {
            module: {
                id_name: 'reorder-columns'
            }
        },
        parameter_vals: [
            {
                id: NEW_REORDER_HISTORY_PAR_ID,
                parameter_spec: {
                    id_name: 'reorder-history'
                },
                value: ''
            }
        ]
    };

    beforeEach(() => {
       api = {
           onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
           addModule: jsonResponseMock(addModuleResponse),
           setSelectedWfModule: jest.fn().mockReturnValue(Promise.resolve())
       };
       mockAPI(api);
       mockStoreApi(api);
       store = {
           getState: () => initialState,
           dispatch: jest.fn().mockReturnValue(Promise.resolve())
       };
       mockStore(store);
    });

    it('Adds a new reorder module after the current non-reorder module '
        + 'if a reorder module does not exist next to it and sets parameters correctly', (done) => {
        updateReorder(LOADURL_WFM_ID, 'test_col', 3, 0);
        setImmediate(() => {
            // Checks the module adding part
            expect(api.addModule.mock.calls).toHaveLength(1);
            // The id of the added module should be reorderModuleId
            expect(api.addModule.mock.calls[0][1]).toBe(initialState.reorderModuleId);
            // The index of the added module should be 1 as we are inserting after the 0th module (loadurl)
            expect(api.addModule.mock.calls[0][2]).toBe(1);

            // Checks the parameter setting part
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toBe(NEW_REORDER_HISTORY_PAR_ID);
            expect(api.onParamChanged.mock.calls[0][1].value).toBe(
                JSON.stringify([{
                    column: 'test_col',
                    from: 3,
                    to: 0
                }])
            );

            done();
        })
    });
})