import React from 'react'
import RenameEntries, {RenameEntry} from './RenameEntries'
import {mount} from 'enzyme'
import {jsonResponseMock} from '../test-utils';

jest.mock('../workflow-reducer')
import { store, deleteModuleAction } from '../workflow-reducer';

describe('RenameEntries rendering and interactions', () => {
    const testEntries = {
        'name': 'host_name',
        'narrative': 'nrtv'
    };

    const columns = ['name', 'build_year', 'narrative', 'cornerstone'];

    const WFM_ID = 1;
    const PARAM_ID = 2;

    let api = null;
    let fetchInputColumns = null

    beforeEach(() => {
        fetchInputColumns = jsonResponseMock(columns)
        api = {
            onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
        };
    });

    it('Adds all columns when initialized empty', (done) => {
        // This test corresponds to behavior when added from module library.
        let tree = mount(<RenameEntries
            fetchInputColumns={fetchInputColumns}
            api={api}
            entriesJsonString={''}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
            isReadOnly={false}
        />);

        setImmediate(() => {
            expect(fetchInputColumns).toHaveBeenCalledWith(WFM_ID);

            // Got the tip to call .update() in this thread:
            // https://github.com/airbnb/enzyme/issues/1233#issuecomment-343449560
            tree.update();

            expect(tree.find('.rename-input')).toHaveLength(4);
            expect(tree.find('.rename-input').get(0).props.value).toEqual('name');
            expect(tree.find('.rename-input').get(1).props.value).toEqual('build_year');
            tree.unmount();
            done();
        });
    });

    it('Displays all columns in entries', (done) => {
        let tree = mount(<RenameEntries
            fetchInputColumns={fetchInputColumns}
            api={api}
            entriesJsonString={JSON.stringify(testEntries)}
            wfModuleId={1}
            paramId={2}
            isReadOnly={false}
        />);

        setImmediate(() => {
            // Got the tip to call .update() in this thread:
            // https://github.com/airbnb/enzyme/issues/1233#issuecomment-343449560
            tree.update();
            expect(tree.find('.rename-input')).toHaveLength(2);
            expect(tree.find('.rename-input').get(0).props.value).toEqual('host_name');
            expect(tree.find('.rename-input').get(1).props.value).toEqual('nrtv');
            tree.unmount();
            done();
        });
    });

    it('Updates parameter upon input completion via blur', (done) => {
        let tree = mount(<RenameEntries
            fetchInputColumns={fetchInputColumns}
            api={api}
            entriesJsonString={JSON.stringify(testEntries)}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
            isReadOnly={false}
        />);

        setImmediate(() => {
            tree.update();
            expect(tree.find('input[value="host_name"]')).toHaveLength(1);
            let yearInput = tree.find('input[value="host_name"]');
            yearInput.simulate('change', {target: {value: 'hn'}});
            yearInput.simulate('blur');
            setImmediate(() => {
                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0]).toHaveLength(2);
                expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
                let updatedEntries = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                expect(updatedEntries['name']).toBe('hn');
                expect(updatedEntries['narrative']).toBe('nrtv');
                tree.unmount();
                done();
            });
        });
    });

    it('Updates parameter upon input completion via enter key', (done) => {
        let tree = mount(<RenameEntries
            fetchInputColumns={fetchInputColumns}
            api={api}
            entriesJsonString={JSON.stringify(testEntries)}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
            isReadOnly={false}
        />);

        setImmediate(() => {
            tree.update();
            expect(tree.find('input[value="host_name"]')).toHaveLength(1);
            let nameInput = tree.find('input[value="host_name"]');
            nameInput.simulate('change', {target: {value: 'host'}});
            nameInput.simulate('keypress', {key: 'Enter'});
            setImmediate(() => {
                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0]).toHaveLength(2);
                expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
                let updatedEntries = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                expect(updatedEntries['name']).toBe('host');
                expect(updatedEntries['narrative']).toBe('nrtv');
                tree.unmount();
                done();
            });
        });
    });

    it('Updates parameter upon deleting an entry', (done) => {
        let tree = mount(<RenameEntries
            fetchInputColumns={fetchInputColumns}
            api={api}
            entriesJsonString={JSON.stringify(testEntries)}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
            isReadOnly={false}
        />);

        setImmediate(() => {
            tree.update();
            expect(tree.find('RenameEntry')).toHaveLength(2);
            // Should be the "name" entry that we will delete next
            let nameEntry = tree.find('RenameEntry').first();
            expect(nameEntry.find('.rename-delete')).toHaveLength(1);
            let deleteBtn = nameEntry.find('.rename-delete');
            deleteBtn.simulate('click');
            setImmediate(() => {
                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0]).toHaveLength(2);
                expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
                let updatedEntries = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                expect(updatedEntries['name']).toBeUndefined();
                expect(updatedEntries['narrative']).toBe('nrtv');
                tree.unmount();
                done();
            });
        });
    });

    it('Deletes itself if all entries are deleted', (done) => {
        const state = {
            workflow: {
                wf_modules: [
                    {
                        id: WFM_ID - 1
                    },
                    {
                        id: WFM_ID
                    }
                ]
            }
        };
        store.getState.mockImplementation(() => state)
        deleteModuleAction.mockImplementation((...args) => [ 'deleteModuleAction', ...args ])

        let tree = mount(<RenameEntries
            fetchInputColumns={fetchInputColumns}
            api={api}
            entriesJsonString={JSON.stringify({'name': 'host_name'})}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
            isReadOnly={false}
        />);

        setImmediate(() => {
            tree.update();
            expect(tree.find('RenameEntry')).toHaveLength(1);
            let firstEntry = tree.find('RenameEntry').first();
            expect(firstEntry.find('.rename-delete')).toHaveLength(1);
            firstEntry.find('.rename-delete').simulate('click');
            expect(store.dispatch).toHaveBeenCalledWith([ 'deleteModuleAction', WFM_ID ]);
            tree.unmount();
            done();
        })
    });
});
