import React, {Component} from 'react';
import Dropzone from 'react-dropzone';
import PropTypes from 'prop-types';
import GJV from 'geojson-validation';
import {OutputIframeCtrl} from "../../OutputIframe";

export default class MapLocationDropZone extends Component {
    // Accepts an upload of GeoJSON file. It is parsed in the front-end because
    // the data load is small and it simplifies the overall logic.
    // The GeoJSON data is stored as a string in the wfModule

    static propTypes = {
        api: PropTypes.shape({
            onParamChanged: PropTypes.func.isRequired,
        }).isRequired,
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
            modified: paramVal.modified,
            alertInvalidFormat: false,
        };
    }

    componentWillReceiveProps(nextProps) {
        if(nextProps.paramData != this.props.paramData) {
            this.setState(this.parseParamDataToState(nextProps.paramData));
        }
    }

    alertInvalidFormat() {
        this.setState({alertInvalidFormat: true});
    }

    refreshIframe() {
        // This slight hack deals with an issue that the iframe does not refresh
        // after a parameter is updated.
        if(OutputIframeCtrl) {
            OutputIframeCtrl.postMessage({refresh: true}, '*');
        }
    }

    updateParamValue(file, geoJSON) {
        let newVal = {
            filename: file.name,
            geojson: geoJSON,
            modified: file.lastModifiedDate
        };
        this.setState({alertInvalidFormat: false}, () => {
            this.props.api.onParamChanged(this.props.paramId, {value: JSON.stringify(newVal)})
            .then(() => {this.refreshIframe()});
        });
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
            return (
                <div>
                    Drop a GeoJSON file here, or click this area to browse and upload from your computer.
                    <br/>
                    GeoJSON files defines the map areas for the choropleth map.
                </div>
            );
        }
        if(this.state.alertInvalidFormat) {
            return (
                <div>
                    <div className={'map-upload-invalid'}>The file you uploaded is not a valid GeoJSON file</div>
                    <div className={'map-upload-invalid-new'}>Click to upload a new file</div>
                </div>
            );
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
                        <div className={'map-geojson-readonly'}>
                            {dropZoneContent}
                        </div>
                    ) : (
                        <Dropzone className={'map-geojson-dropzone'}
                            onDrop={this.onDrop}
                        >
                            {dropZoneContent}
                        </Dropzone>
                )}
            </div>
        );
    }
}