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
            expect(api.addModule).toHaveBeenCalledWith(WF_ID, initialState.renameModuleId, 1);

            // Checks the parameter setting part, which should have two parts:
            // 1. Setting loadAll to false
            // 2. Setting the new rename entries
            expect(api.onParamChanged.mock.calls).toHaveLength(2);
            // Check that we set loadAll to false
            expect(api.onParamChanged).toHaveBeenCalledWith(NEW_RENAME_DISPLAY_ALL_PAR_ID, {value: false});
            // Check that we set the new entries
            expect(api.onParamChanged).toHaveBeenCalledWith(NEW_RENAME_ENTRIES_ID, {value: JSON.stringify({'cornerstone': 'cs'})});

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
            expect(api.onParamChanged).toHaveBeenCalledWith(
                RENAME_ENTRIES_ID,
                {
                    value: JSON.stringify({
                        'name': 'host_name',
                        'narrative': 'nrtv',
                        'cornerstone': 'cs'
                    })
                }
            );

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

            // Checks that we have properly modified the entry
            // We should only have one call that updates the entries
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged).toHaveBeenCalledWith(
                RENAME_ENTRIES_ID,
                {
                    value: JSON.stringify({
                        'name': 'host',
                        'narrative': 'nrtv',
                    })
                }
            );

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
            expect(api.onParamChanged).toHaveBeenCalledWith(
                RENAME_ENTRIES_ID,
                {
                    value: JSON.stringify({
                        'name': 'host_name',
                        'narrative': 'nrtv',
                        'cornerstone': 'cs'
                    })
                }
            );

            done();
        });
    });
});