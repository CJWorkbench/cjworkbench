import {updateRename, mockAPI} from "./RenameColumns";
import {mockStore, mockAPI as mockStoreAPI} from "./workflow-reducer";
import {jsonResponseMock} from "./test-utils";

describe('RenameColumns actions', () => {
    var store, api;

    // A few parameter id constants for readability
    const LOADURL_WFM_ID = 35;

    const FILTER_WFM_ID = 50;

    const RENAME_WFM_ID = 85;
    const RENAME_DISPLAY_ALL_PAR_ID = 90;
    const RENAME_ENTRIES_ID = 105;

    const NEW_RENAME_WFM_ID = 120;
    const NEW_RENAME_DISPLAY_ALL_PAR_ID = 135;
    const NEW_RENAME_ENTRIES_ID = 150;

    const RENAME_MODULE_ID = 24;
    const WF_ID = 18;

    var initialState = {
        renameModuleId: RENAME_MODULE_ID,
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
                            id_name: 'rename-columns'
                        }
                    },
                    parameter_vals: [
                        {
                            id: RENAME_DISPLAY_ALL_PAR_ID,
                            parameter_spec: {
                                id_name: 'display-all'
                            },
                            // value will always be false after initial load
                            value: false
                        },
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
                id_name: 'rename-columns'
            }
        },
        parameter_vals: [
            {
                id: NEW_RENAME_DISPLAY_ALL_PAR_ID,
                parameter_spec: {
                    id_name: 'display-all'
                },
                // value defaults to true when just added
                value: true
            },
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
        api = {
            onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
            addModule: jsonResponseMock(addModuleResponse),
            setSelectedWfModule: jest.fn().mockReturnValue(Promise.resolve())
        };
        mockAPI(api);
        mockStoreAPI(api);
        store = {
            getState: () => initialState,
            dispatch: jest.fn().mockReturnValue(Promise.resolve())
        };
        mockStore(store);
    });

    it('Adds a new rename module after the current non-rename module '
        + 'if a rename module does not after it and sets parameters correctly', (done) => {
        updateRename(LOADURL_WFM_ID, {
            prevName: 'cornerstone',
            newName: 'cs'
        });
        // The entries that should be sent to server is {'cornerstone': 'cs'}
        setImmediate(() => {
            // Checks the module adding part
            expect(api.addModule.mock.calls).toHaveLength(1);
            // The id of the added module should be renameModuleId
            expect(api.addModule.mock.calls[0][1]).toBe(initialState.renameModuleId);
            // The index of the added module should be 1 as we are inserting after the 0th module (loadurl)
            expect(api.addModule.mock.calls[0][2]).toBe(1);

            // Checks the parameter setting part, which should have two parts:
            // 1. Setting loadAll to false
            // 2. Setting the new rename entries
            expect(api.onParamChanged.mock.calls).toHaveLength(2);
            // Check that we set loadAll to false
            expect(api.onParamChanged.mock.calls[0][0]).toBe(NEW_RENAME_DISPLAY_ALL_PAR_ID);
            expect(api.onParamChanged.mock.calls[0][1].value).toBe(false);
            // Check that we set the new entries
            expect(api.onParamChanged.mock.calls[1][0]).toBe(NEW_RENAME_ENTRIES_ID);
            let changedParams = JSON.parse(api.onParamChanged.mock.calls[1][1].value);
            expect(Object.keys(changedParams)).toHaveLength(1);
            expect(changedParams['cornerstone']).toBe('cs');

            done();
        });
    });

    it('Adds a new renamed column to an existing rename module correctly', (done) => {
        updateRename(FILTER_WFM_ID, {
            prevName: 'cornerstone',
            newName: 'cs'
        });
        /*
            New entries should be
            {
                'name': 'host_name',
                'narrative': 'nrtv',
                'cornerstone: 'cs'
            }
         */
        setImmediate(() => {
            // No new module should be added as there is an existing rename module next to it
            expect(api.addModule.mock.calls).toHaveLength(0);

            // Checks that we have added the new entry
            // We should only have one call that updates the entries
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toBe(RENAME_ENTRIES_ID);
            let changedParams = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
            expect(Object.keys(changedParams)).toHaveLength(3);
            expect(changedParams['name']).toBe('host_name');
            expect(changedParams['narrative']).toBe('nrtv');
            expect(changedParams['cornerstone']).toBe('cs');

            done();
        });
    });

    it('Renames an already renamed entry in an existing rename module correctly', (done) => {
        updateRename(FILTER_WFM_ID, {
            prevName: 'host_name',
            newName: 'host'
        });
        /*
            New entries should be
            {
                'name': 'host',
                'narrative': 'nrtv',
            }
         */
        setImmediate(() => {
            // No new module should be added as there is an existing rename module next to it
            expect(api.addModule.mock.calls).toHaveLength(0);

            // Checks that we have added the new entry
            // We should only have one call that updates the entries
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toBe(RENAME_ENTRIES_ID);
            let changedParams = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
            expect(Object.keys(changedParams)).toHaveLength(2);
            expect(changedParams['name']).toBe('host');
            expect(changedParams['narrative']).toBe('nrtv');

            done();
        })
    });

    it('Updates the parameter values of the currently selected rename module correctly', (done) => {
        updateRename(RENAME_WFM_ID, {
            prevName: 'cornerstone',
            newName: 'cs'
        });
        /*
            New entries should be
            {
                'name': 'host_name',
                'narrative': 'nrtv',
                'cornerstone: 'cs'
            }
         */
        setImmediate(() => {
            // No new module should be added as there is an existing rename module next to it
            expect(api.addModule.mock.calls).toHaveLength(0);

            // Checks that we have added the new entry
            // We should only have one call that updates the entries
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toBe(RENAME_ENTRIES_ID);
            let changedParams = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
            expect(Object.keys(changedParams)).toHaveLength(3);
            expect(changedParams['name']).toBe('host_name');
            expect(changedParams['narrative']).toBe('nrtv');
            expect(changedParams['cornerstone']).toBe('cs');

            done();
        });
    });
});