import React from 'react'
import MapLocationDropZone from './MapLocationDropZone'
import {shallow} from 'enzyme'
import Dropzone from 'react-dropzone'


// The following tests utilized the class names in MapLocationDropZone.
// If you update the class names, please update the tests accordingly.


describe('MapLocationDropZone rendering tests', () => {
    const PARAM_NAME = 'Upload geoJSON';
    const PARAM_ID = 7;
    const mockParamData = {
        filename: 'test.js',
        geojson: {},
        modified: new Date(2018, 4, 22, 9, 0)
    };

    it('Renders an empty dropzone on initial load', () => {
        let tree = shallow(<MapLocationDropZone name={PARAM_NAME} paramData={''} paramId={PARAM_ID} isReadOnly={false}/>);
        expect(tree.find(Dropzone)).toHaveLength(1);
        expect(tree.find('div.map-uploaded-filename')).toHaveLength(0);
        expect(tree.find('div.map-uploaded-date')).toHaveLength(0);
        expect(tree.find('div.map-upload-new')).toHaveLength(0);
    });

    it('Renders a dropzone that shows previously uploaded files according to param data', () => {
        let tree = shallow(
            <MapLocationDropZone
                name={PARAM_NAME}
                paramData={JSON.stringify(mockParamData)}
                paramId={PARAM_ID}
                isReadOnly={false}
            />
        );
        expect(tree.find(Dropzone)).toHaveLength(1);
        // Name field
        expect(tree.find('div.map-uploaded-filename')).toHaveLength(1);
        expect(tree.find('div.map-uploaded-filename').text()).toEqual('test.js');
        // Check that we have a date field and a prompt to upload new
        // We don't check the values here as the prompt and date format might be subject to change
        expect(tree.find('div.map-uploaded-date')).toHaveLength(1);
        expect(tree.find('div.map-upload-new')).toHaveLength(1);
    });

    it('Renders a placeholder div instead of a dropzone for a read-only module', () => {
        let tree = shallow(
            <MapLocationDropZone
                name={PARAM_NAME}
                paramData={JSON.stringify(mockParamData)}
                paramId={PARAM_ID}
                isReadOnly={true}
            />
        );
        // We should not be finding a Dropzone here
        expect(tree.find(Dropzone)).toHaveLength(0);
        // Instead we will find a placeholder div
        expect(tree.find('div.map-geojson-readonly')).toHaveLength(1);
        // We should have all the other fields for an uploaded GeoJSON file
        // Name field
        expect(tree.find('div.map-uploaded-filename')).toHaveLength(1);
        expect(tree.find('div.map-uploaded-filename').text()).toEqual('test.js');
        // Check that we have a date field and a prompt to upload new
        // We don't check the values here as the prompt and date format might be subject to change
        expect(tree.find('div.map-uploaded-date')).toHaveLength(1);
        expect(tree.find('div.map-upload-new')).toHaveLength(1);
    });
});