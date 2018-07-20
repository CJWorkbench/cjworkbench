import React, {Component} from 'react'
import {store, setWfModuleStatusAction} from "../../workflow-reducer"
import Dropzone from 'react-dropzone'
import PropTypes from 'prop-types'
import GJV from 'geojson-validation'
import WorkBenchAPI from '../../WorkbenchAPI'

import 'react-fine-uploader/gallery/gallery.css'
import DropZone from "../DropZone";

var api = WorkBenchAPI();

export default class MapLocationDropZone extends Component {
    // Accepts an upload of GeoJSON file. It is parsed in the front-end because
    // the data load is small and it simplifies the overall logic.
    // The GeoJSON data is stored as a string in the wfModule

    static propTypes = {
        name: PropTypes.string.isRequired,
        paramData: PropTypes.string.isRequired,
        paramId: PropTypes.number.isRequired,
        isReadOnly: PropTypes.bool.isRequired
    };

    constructor(props) {
        super(props);

        this.state = this.parseParamDataToState(props.paramData);

        this.onDrop = this.onDrop.bind(this);
    }

    parseParamDataToState(paramData) {
        let paramVal = {};
        let isEmpty = false;
        try {
            paramVal = JSON.parse(paramData);
        } catch(e) {
            isEmpty = true;
        }

        return {
            isEmpty: isEmpty,
            filename: paramVal.filename,
            modified: paramVal.modified
        };
    }

    componentDidMount() {
    }

    componentWillReceiveProps(nextProps) {
        if(nextProps.paramData != this.props.paramData) {
            this.setState(this.parseParamDataToState(nextProps.paramData));
        }
    }

    alertInvalidFormat() {
        console.log("Uploaded file is not valid geoJSON.");
    }

    updateParamValue(file, geoJSON) {
        let newVal = {
            filename: file.name,
            geojson: geoJSON,
            modified: file.lastModifiedDate
        };
        api.onParamChanged(this.props.paramId, {value: JSON.stringify(newVal)});
    }

    onDrop(acceptedFiles, rejectedFiles) {
        if(acceptedFiles.length < 1) {
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const geoJSONString = reader.result;
            try {
                const geoJSON = JSON.parse(geoJSONString);
                if(GJV.valid(geoJSON)) {
                    this.updateParamValue(acceptedFiles[0], geoJSON);
                } else {
                    this.alertInvalidFormat();
                }
            } catch(e) {
                this.alertInvalidFormat();
            }
        };
        reader.onerror = () => {
            this.alertInvalidFormat();
        };

        reader.readAsText(acceptedFiles[0]);
    }

    renderDropZoneContent() {
        if(this.state.isEmpty) {
            return 'Drop a GeoJSON file here, or click this area to browse and upload from your computer.\n' +
                'GeoJSON files defines the map areas for the choropleth map.'
        }
        return (
            <div>
                <div className={'map-uploaded-filename'}>{this.state.filename}</div>
                <div className={'map-uploaded-date'}>{this.state.modified}</div>
                <div className={'map-upload-new'}>Click to upload a new file</div>
            </div>
        );
    }

    render() {
        const dropZoneContent = this.renderDropZoneContent();

        return (
            <div>
                <div className='label-margin t-d-gray content-3'>{this.props.name}</div>
                {this.props.isReadOnly ? (
                        <div>
                            {dropZoneContent}
                        </div>
                    ) : (
                        <Dropzone
                            onDrop={this.onDrop}
                        >
                            {dropZoneContent}
                        </Dropzone>
                )}
            </div>
        );
    }
}