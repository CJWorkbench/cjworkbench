import React from 'react'
import MapLocationPresets from './MapLocationPresets'
import {mount, shallow} from 'enzyme'
import GJV from 'geojson-validation'


const tick = async() => new Promise(resolve => setTimeout(resolve, 0));

describe('MapLocationPresets rendering and interactions', () => {
    const PARAM_ID = 11;
    const PARAM_NAME = 'Presets';

    var api;

    beforeEach(() => {
        api = {
            onParamChanged: jest.fn().mockReturnValue(Promise.resolve())
        };
    });

    it('Renders the select widgets with presets and selects "select" if parameter is empty', () => {
        let tree = shallow(<MapLocationPresets api={api} paramData={''} paramId={PARAM_ID} name={PARAM_NAME} isReadOnly={false}/>);

        expect(tree.find('select')).toHaveLength(1);
        expect(tree.find('select').prop('value')).toEqual('select');

        // If they are removed, update the tests here.
        let presetOptions = [];
        tree.find('option').forEach((node) => {
            presetOptions.push(node.prop('value'));
        });
        expect(presetOptions.includes('select')).toBe(true);
        expect(presetOptions.includes('us-states')).toBe(true);
    });

    it('Renders the previously-selected preset according to parameter data', () => {
        // The following test assume that the "us-states" preset exist.
        // If it is removed, update the tests here.

        let tree = shallow(
            <MapLocationPresets
                paramData={JSON.stringify({preset: 'us-states', geojson: {}})}
                paramId={PARAM_ID} name={PARAM_NAME} isReadOnly={false} api={api}/>
        );

        expect(tree.find('select')).toHaveLength(1);
        expect(tree.find('select').prop('value')).toEqual('us-states');
    });

    it('Updates the server with proper GeoJSON upon selecting a preset', async () => {
        let tree = mount(<MapLocationPresets api={api} paramData={''} paramId={PARAM_ID} name={PARAM_NAME} isReadOnly={false}/>);

        expect(tree.find('select')).toHaveLength(1);

        // The following test assume that the "us-states" preset exist.
        // If it is removed, update the tests here.
        let selector = tree.find('select');
        selector.simulate('change', {target: {value: 'us-states'}});
        await tick();
        expect(api.onParamChanged.mock.calls).toHaveLength(1);
        expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
        let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
        expect(paramData.preset).toEqual('us-states');
        // For convenience's sake we will only check that the GeoJSON is proper GeoJSON, as it should be
        expect(GJV.valid(paramData.geojson)).toBe(true);

        tree.unmount();
    });

    it('Updates the server with empty data upon selecting "select"', async () => {
        let tree = mount(<MapLocationPresets api={api} paramData={''} paramId={PARAM_ID} name={PARAM_NAME} isReadOnly={false}/>);

        expect(tree.find('select')).toHaveLength(1);

        // Test by selecting the "select"
        let selector = tree.find('select');
        selector.simulate('change', {target: {value: 'select'}});
        await tick();
        expect(api.onParamChanged.mock.calls).toHaveLength(1);
        expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
        let paramStr = api.onParamChanged.mock.calls[0][1].value;
        expect(paramStr).toEqual('');
    });

    it('Respects the isReadOnlySetting', () => {
        let readOnlyTree = mount(<MapLocationPresets api={api} paramData={''} paramId={PARAM_ID} name={PARAM_NAME} isReadOnly={true}/>);
        expect(readOnlyTree.find('select')).toHaveLength(1);
        expect(readOnlyTree.find('select').prop('disabled')).toBe(true);

        let modifiableTree = mount(<MapLocationPresets api={api} paramData={''} paramId={PARAM_ID} name={PARAM_NAME} isReadOnly={false}/>);
        expect(modifiableTree.find('select')).toHaveLength(1);
        expect(modifiableTree.find('select').prop('disabled')).toBe(false);
    });
});
