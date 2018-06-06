import React from 'react'
import RenameEntries, {RenameEntry, mockAPI} from './RenameEntries'
import {mount, shallow} from 'enzyme'
import {jsonResponseMock} from "../test-utils";


describe('ReorderEntries rendering and interactions', () => {
    const testEntries = {
        'name': 'host_name',
        'narrative': 'nrtv'
    };

    const columns = ['name', 'build_year', 'narrative', 'cornerstone'];

    const WFM_ID = 1;
    const PARAM_ID = 2;

    var api = undefined;

    beforeEach(() => {
        api = {
            inputColumns: jsonResponseMock(columns),
            onParamChanged: jest.fn().mockReturnValue(Promise.resolve())
        };
        mockAPI(api);
    });

    it('Displays all columns when displayAll is set to true', (done) => {
        let tree = mount(<RenameEntries
            displayAll={true}
            entries={JSON.stringify({})}
            wfModuleId={1}
            paramId={2}
        />);

        setImmediate(() => {
            // Got the tip to call .update() in this thread:
            // https://github.com/airbnb/enzyme/issues/1233#issuecomment-343449560
            tree.update();
            expect(tree.find('.rename-input')).toHaveLength(4);
            expect(tree.find('.rename-input').get(0).props.value).toEqual('name');
            expect(tree.find('.rename-input').get(1).props.value).toEqual('build_year');
            expect(tree.find('.rename-input').get(2).props.value).toEqual('narrative');
            expect(tree.find('.rename-input').get(3).props.value).toEqual('cornerstone');
            tree.unmount();
            done();
        });
    });

    it('Displays changed columns properly when displayAll is set to true', (done) => {
        let tree = mount(<RenameEntries
            displayAll={true}
            entries={JSON.stringify(testEntries)}
            wfModuleId={1}
            paramId={2}
        />);

        setImmediate(() => {
            // Got the tip to call .update() in this thread:
            // https://github.com/airbnb/enzyme/issues/1233#issuecomment-343449560
            tree.update();
            expect(tree.find('.rename-input')).toHaveLength(4);
            expect(tree.find('.rename-input').get(0).props.value).toEqual('host_name');
            expect(tree.find('.rename-input').get(1).props.value).toEqual('build_year');
            expect(tree.find('.rename-input').get(2).props.value).toEqual('nrtv');
            expect(tree.find('.rename-input').get(3).props.value).toEqual('cornerstone');
            tree.unmount();
            done();
        });
    });

    it('Only displays changed columns when displayAll is set to false', (done) => {
        let tree = mount(<RenameEntries
            displayAll={false}
            entries={JSON.stringify(testEntries)}
            wfModuleId={1}
            paramId={2}
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
            displayAll={true}
            entries={JSON.stringify(testEntries)}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
        />);

        setImmediate(() => {
            tree.update();
            expect(tree.find('input[value="build_year"]')).toHaveLength(1);
            let yearInput = tree.find('input[value="build_year"]');
            yearInput.simulate('change', {target: {value: 'year'}});
            yearInput.simulate('blur');
            setImmediate(() => {
                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0]).toHaveLength(2);
                expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
                let updatedEntries = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                expect(updatedEntries['name']).toBe('host_name');
                expect(updatedEntries['build_year']).toBe('year');
                expect(updatedEntries['narrative']).toBe('nrtv');
                tree.unmount();
                done();
            });
        });
    });

    it('Updates parameter upon input completion via enter key', (done) => {
        let tree = mount(<RenameEntries
            displayAll={true}
            entries={JSON.stringify(testEntries)}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
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
            displayAll={true}
            entries={JSON.stringify(testEntries)}
            wfModuleId={WFM_ID}
            paramId={PARAM_ID}
        />);

        setImmediate(() => {
            tree.update();
            expect(tree.find('RenameEntry')).toHaveLength(4);
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
});