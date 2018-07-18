import React from 'react'
import MapLocationPresets, {mockAPI} from './MapLocationPresets'
import {mount, shallow} from 'enzyme'
import GJV from 'geojson-validation'


describe('MapLocationPresets rendering and interactions', () => {
    const PARAM_ID = 11;
    const PARAM_NAME = 'Presets';

    var api = undefined;

    beforeEach(() => {
        api = {
            onParamChanged: jest.fn().mockReturnValue(Promise.resolve())
        };
        mockAPI(api);
    });

    it('Renders the select widgets with presets and selects "select" if parameter is empty', () => {
        let tree = shallow(<MapLocationPresets paramData={''} paramId={PARAM_ID} name={PARAM_NAME}/>);

        expect(tree.find('select')).toHaveLength(1);
        expect(tree.find('select').prop('value')).toEqual('select');

        // The following test assume that "us-states" and "nyc-precincts" presets exist.
        // If they are removed, update the tests here.
        let presetOptions = [];
        tree.find('option').forEach((node) => {
            presetOptions.push(node.prop('value'));
        });
        expect(presetOptions.includes('select')).toBe(true);
        expect(presetOptions.includes('us-states')).toBe(true);
        expect(presetOptions.includes('nyc-precincts')).toBe(true);
    });

    it('Renders the previously-selected preset according to parameter data', () => {
        // The following test assume that the "us-states" preset exist.
        // If it is removed, update the tests here.

        let tree = shallow(
            <MapLocationPresets
                paramData={JSON.stringify({preset: 'us-states', geojson: {}})}
                paramId={PARAM_ID} name={PARAM_NAME}/>
        );

        expect(tree.find('select')).toHaveLength(1);
        expect(tree.find('select').prop('value')).toEqual('us-states');
    });

    it('Updates the server with proper GeoJSON upon selecting a preset', (done) => {
        let tree = mount(<MapLocationPresets paramData={''} paramId={PARAM_ID} name={PARAM_NAME}/>);

        expect(tree.find('select')).toHaveLength(1);

        // The following test assume that the "us-states" preset exist.
        // If it is removed, update the tests here.
        let selector = tree.find('select');
        selector.simulate('change', {target: {value: 'us-states'}});
        setImmediate(() => {
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
            let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
            expect(paramData.preset).toEqual('us-states');
            // For convenience's sake we will only check that the GeoJSON is proper GeoJSON, as it should be
            expect(GJV.valid(paramData.geojson)).toBe(true);
            done();
        });
    });

    it('Updates the server with empty data upon selecting "select"', (done) => {
        let tree = mount(<MapLocationPresets paramData={''} paramId={PARAM_ID} name={PARAM_NAME}/>);

        expect(tree.find('select')).toHaveLength(1);

        // Test by selecting the "select"
        let selector = tree.find('select');
        selector.simulate('change', {target: {value: 'select'}});
        setImmediate(() => {
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toBe(PARAM_ID);
            let paramStr = api.onParamChanged.mock.calls[0][1].value;
            expect(paramStr).toEqual('');
            done();
        });
    })
});
