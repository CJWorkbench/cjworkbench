import React from 'react'
import MapLayerEditor, {SingleMapLayerEditor, mockAPI} from "./MapLayerEditor"
import {mount} from 'enzyme'
import {jsonResponseMock} from "../../test-utils"
import {CirclePicker} from 'react-color'


// These tests utilizes the class names in MapLayerEditor.js.
// If they are changed, please update the tests here accordingly.


describe('MapLayerEditor rendering and interactions', () => {
    const PARAM_ID = 17;
    const WFM_ID = 23;
    const PARAM_NAME = 'Layers';

    var api = undefined;

    const mockExistingParamData = {
        lastEdited: 'value1',
        layers: {
            'location': {
                color: '#F44336',
                levels: 5,
                selected: true,
            },
            'value1': {
                color: '#F44336',
                levels: 7,
                selected: true,
            },
            'value2': {
                color: '#FF9800',
                levels: 5,
                selected: false,
            },
        }
    };

    const mockDefaultColumns = ['location', 'value1', 'value2'];
    const mockChangedColumns = ['location', 'value1', 'value2', 'value3'];

    beforeEach(() => {
        api = {
            onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
            inputColumns: jsonResponseMock(mockDefaultColumns)
        };
        mockAPI(api);
    });

    it('Does not render anything upon initial load without key column, but updates the server with default map appearance', (done) => {
        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={''}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={''}
            />
        );

        setImmediate(() => {
            // No SingleMapLayerEditor should be rendered
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(0);

            // The module should inquire the server about input columns
            expect(api.inputColumns).toHaveBeenCalledWith(WFM_ID);

            // The server should be updated with the default setting for each potential layer
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toEqual(PARAM_ID);

            // Check the parameter update content
            let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
            // lastEdited should not be set because no edits have happened yet
            expect(paramData.lastEdited).toBeUndefined();
            // All columns/layers should have the default appearance:
            // 5 levels, visible, color #F44336 (red)
            // If the default appearance is changed, please update the test here
            Object.keys(paramData.layers).forEach((key) => {
                expect(mockDefaultColumns.includes(key)).toBe(true);
                expect(paramData.layers[key]).toBeDefined();
                expect(paramData.layers[key].color).toEqual('#F44336');
                expect(paramData.layers[key].selected).toBe(true);
                expect(paramData.layers[key].levels).toEqual(5);
            });
            expect(Object.keys(paramData.layers).length).toEqual(mockDefaultColumns.length);

            done();
        });
    });

    it('Does not update the server upon loading existing data if columns don\'t change', (done) => {
        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={''}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={JSON.stringify(mockExistingParamData)}
            />
        );

        setImmediate(() => {
            // No SingleMapLayerEditor should be rendered
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(0);

            // The module should inquire the server about input columns
            expect(api.inputColumns).toHaveBeenCalledWith(WFM_ID);

            // The module should not update the server because columns haven't changed
            expect(api.onParamChanged.mock.calls).toHaveLength(0);

            done();
        })
    });

    it('Gives a newly appearing column the default settings upon load', (done) => {
        // Modify the mock API to return new columns
        api.inputColumns = jsonResponseMock(mockChangedColumns);
        mockAPI(api);

        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={''}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={JSON.stringify(mockExistingParamData)}
            />
        );

        setImmediate(() => {
            // No SingleMapLayerEditor should be rendered
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(0);

            // The module should inquire the server about input columns
            expect(api.inputColumns).toHaveBeenCalledWith(WFM_ID);

            // The server should be updated with the default setting for each potential layer
            expect(api.onParamChanged.mock.calls).toHaveLength(1);
            expect(api.onParamChanged.mock.calls[0][0]).toEqual(PARAM_ID);

            // Check the parameter update content
            let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
            // lastEdited should be 'value1', according to the existing data
            expect(paramData.lastEdited).toEqual('value1');
            Object.keys(paramData.layers).forEach((key) => {
                expect(paramData.layers[key]).toBeDefined();
                if(mockDefaultColumns.includes(key)) {
                    // Check that existing columns' settings are preserved
                    expect(paramData.layers[key].color).toEqual(mockExistingParamData.layers[key].color);
                    expect(paramData.layers[key].selected).toBe(mockExistingParamData.layers[key].selected);
                    expect(paramData.layers[key].levels).toEqual(mockExistingParamData.layers[key].levels);
                } else {
                    // Check that this is the new column, and it uses the default settings
                    // of 5 levels, red and selected
                    expect(key).toEqual('value3');
                    expect(paramData.layers[key].color).toEqual('#F44336');
                    expect(paramData.layers[key].selected).toBe(true);
                    expect(paramData.layers[key].levels).toEqual(5);
                }
            });
            expect(Object.keys(paramData.layers).length).toEqual(mockChangedColumns.length);

            done();
        });
    });

    it('Renders editor for all columns but the key column when a key column is selected', (done) => {
        // layerColumns should render, keyColumn should not
        let keyColumn = 'location';
        let layerColumns = mockDefaultColumns.filter((col) => (col !== keyColumn));

        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={keyColumn}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={JSON.stringify(mockExistingParamData)}
            />
        );

        setImmediate(() => {
            tree.update();

            // We should have two layers
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(2);

            // Check that the layers are for columns we wanted
            // and that they have the proper components.
            tree.find(SingleMapLayerEditor).forEach((node) => {
                expect(layerColumns.includes(node.prop('column'))).toBe(true);

                let column = node.prop('column');

                // Color picker
                expect(node.find(CirclePicker)).toHaveLength(1);
                expect(node.find(CirclePicker).prop('color')).toEqual(mockExistingParamData.layers[column].color);

                // "selected" checkbox
                expect(node.find('input.map-layer-checkbox')).toHaveLength(1);
                expect(node.find('input.map-layer-checkbox').prop('checked')).toBe(mockExistingParamData.layers[column].selected);

                // "levels" input
                expect(node.find('input.map-layer-levels-input')).toHaveLength(1);
                expect(node.find('input.map-layer-levels-input').prop('value')).toBe(mockExistingParamData.layers[column].levels);
            });

            done();
        });
    });

    it('Updates the server upon a layer selection change', (done) => {
        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={'location'}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={JSON.stringify(mockExistingParamData)}
            />
        );

        setImmediate(() => {
            tree.update();

            // We should have two layers
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(2);

            // We test this on 'value2'
            let target = 'value2';

            let targetEditor = tree.find(SingleMapLayerEditor).find({column: target});
            expect(targetEditor).toHaveLength(1);
            let targetCheckbox = targetEditor.find('input.map-layer-checkbox');
            expect(targetCheckbox).toHaveLength(1);
            // The box's status should conform to existing data
            expect(targetCheckbox.prop('checked')).toBe(mockExistingParamData.layers[target].selected);

            targetCheckbox.simulate('change');
            setImmediate(() => {
                tree.update();

                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0][0]).toEqual(PARAM_ID);
                let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                // We changed our target layer so it should be the lastEdited value
                expect(paramData.lastEdited).toEqual(target);
                Object.keys(paramData.layers).forEach((col) => {
                    if(col !== target) {
                        // Other layers should remain the same
                        expect(paramData.layers[col]).toEqual(mockExistingParamData.layers[col]);
                    } else {
                        // Target layer should be updated
                        // Color and levels should be unchanged
                        expect(paramData.layers[col].color).toEqual(mockExistingParamData.layers[col].color);
                        expect(paramData.layers[col].levels).toEqual(mockExistingParamData.layers[col].levels);
                        // "selected" should flip
                        expect(paramData.layers[col].selected).toBe(!mockExistingParamData.layers[target].selected);
                    }
                });
                done();
            });
        });
    });

    it('Updates the server upon a layer levels change, completed via blur event', (done) => {
        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={'location'}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={JSON.stringify(mockExistingParamData)}
            />
        );

        setImmediate(() => {
            tree.update();

            // We should have two layers
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(2);

            // We test this on 'value2'
            let target = 'value2';

            let targetEditor = tree.find(SingleMapLayerEditor).find({column: target});
            expect(targetEditor).toHaveLength(1);
            let targetInput = targetEditor.find('input.map-layer-levels-input');
            expect(targetInput).toHaveLength(1);
            // The value should conform to existing data
            expect(targetInput.prop('value')).toBe(mockExistingParamData.layers[target].levels);

            let newLevelsVal = 11;
            targetInput.simulate('change', {target: {value: newLevelsVal}});
            targetInput.simulate('blur');
            setImmediate(() => {
                tree.update();

                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0][0]).toEqual(PARAM_ID);
                let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                // We changed 'value2' so it should be the lastEdited value
                expect(paramData.lastEdited).toEqual(target);
                Object.keys(paramData.layers).forEach((col) => {
                    if(col !== target) {
                        // Other layers should remain the same
                        expect(paramData.layers[col]).toEqual(mockExistingParamData.layers[col]);
                    } else {
                        // 'value2' layer should be updated
                        // Color and selected should be unchanged
                        expect(paramData.layers[col].color).toEqual(mockExistingParamData.layers[col].color);
                        expect(paramData.layers[col].selected).toBe(mockExistingParamData.layers[col].selected);
                        // Levels should go to the new value
                        expect(paramData.layers[col].levels).toEqual(newLevelsVal);
                    }
                });
                done();
            });
        });
    });

    it('Updates the server upon a layer levels change, completed via pressing Enter', (done) => {
        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={'location'}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={JSON.stringify(mockExistingParamData)}
            />
        );

        setImmediate(() => {
            tree.update();

            // We should have two layers
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(2);

            // We test this on 'value2'
            let target = 'value2';

            let targetEditor = tree.find(SingleMapLayerEditor).find({column: target});
            expect(targetEditor).toHaveLength(1);
            let targetInput = targetEditor.find('input.map-layer-levels-input');
            expect(targetInput).toHaveLength(1);
            // The value should conform to existing data
            expect(targetInput.prop('value')).toBe(mockExistingParamData.layers[target].levels);

            let newLevelsVal = 11;
            targetInput.simulate('change', {target: {value: newLevelsVal}});
            targetInput.simulate('keypress', {key: 'Enter'});
            setImmediate(() => {
                tree.update();

                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0][0]).toEqual(PARAM_ID);
                let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                // We changed 'value2' so it should be the lastEdited value
                expect(paramData.lastEdited).toEqual(target);
                Object.keys(paramData.layers).forEach((col) => {
                    if(col !== target) {
                        // Other layers should remain the same
                        expect(paramData.layers[col]).toEqual(mockExistingParamData.layers[col]);
                    } else {
                        // 'value2' layer should be updated
                        // Color and selected should be unchanged
                        expect(paramData.layers[col].color).toEqual(mockExistingParamData.layers[col].color);
                        expect(paramData.layers[col].selected).toBe(mockExistingParamData.layers[col].selected);
                        // Levels should go to the new value
                        expect(paramData.layers[col].levels).toEqual(newLevelsVal);
                    }
                });
                done();
            });
        });
    });

    it('Updates the server upon a color change', (done) => {
        let tree = mount(
            <MapLayerEditor
                name={PARAM_NAME}
                paramId={PARAM_ID}
                keyColumn={'location'}
                wfModuleId={WFM_ID}
                isReadOnly={false}
                paramData={JSON.stringify(mockExistingParamData)}
            />
        );

        setImmediate(() => {
            tree.update();

            // We should have two layers
            expect(tree.find(SingleMapLayerEditor)).toHaveLength(2);

            // We test this on 'value2'
            let target = 'value2';

            let targetEditor = tree.find(SingleMapLayerEditor).find({column: target});
            expect(targetEditor).toHaveLength(1);
            let targetColorPicker = targetEditor.find(CirclePicker);
            expect(targetColorPicker).toHaveLength(1);
            // The value should conform to existing data
            expect(targetColorPicker.prop('color')).toBe(mockExistingParamData.layers[target].color);

            let newColor = '#009688';
            targetColorPicker.props().onChangeComplete({hex: newColor});
            setImmediate(() => {
                tree.update();

                expect(api.onParamChanged.mock.calls).toHaveLength(1);
                expect(api.onParamChanged.mock.calls[0][0]).toEqual(PARAM_ID);
                let paramData = JSON.parse(api.onParamChanged.mock.calls[0][1].value);
                // We changed 'value2' so it should be the lastEdited value
                expect(paramData.lastEdited).toEqual(target);
                Object.keys(paramData.layers).forEach((col) => {
                    if(col !== target) {
                        // Other layers should remain the same
                        expect(paramData.layers[col]).toEqual(mockExistingParamData.layers[col]);
                    } else {
                        // 'value2' layer should be updated
                        // Levels and selected should be unchanged
                        expect(paramData.layers[col].levels).toEqual(mockExistingParamData.layers[col].levels);
                        expect(paramData.layers[col].selected).toBe(mockExistingParamData.layers[col].selected);
                        // Color should go to the new value
                        expect(paramData.layers[col].color).toEqual(newColor);
                    }
                });
                done();
            });
        });
    });
});