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
});