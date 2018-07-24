import React, {Component} from 'react';
import Dropzone from 'react-dropzone';
import PropTypes from 'prop-types';
import GJV from 'geojson-validation';


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
    }

    componentWillReceiveProps(nextProps) {
        if(nextProps.paramData !== this.props.paramData) {
            this.setState(this.parseParamDataToState(nextProps.paramData));
        }
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
            geojson: paramVal.geojson,
            properties: paramVal.properties,       // Potential property names to correlate to location column
            keyProperty: paramVal.keyProperty,     // Selected property name to correlate to location column
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

    handlePropertySelectionChange = (event) => {
        let newKeyProperty = event.target.value;
        let newVal = {
            filename: this.state.filename,
            modified: this.state.modified,
            geojson: this.state.geojson,
            properties: this.state.properties,
            keyProperty: event.target.value
        };
        this.setState({keyProperty: newKeyProperty},
            () => {this.props.api.onParamChanged(this.props.paramId, {value: JSON.stringify(newVal)})});
    };

    updateParamValue(file, geoJSON) {
        if(geoJSON.features.length < 1) {
            // We don't consider a GeoJSON file valid if it doesn't have features
            this.alertInvalidFormat();
            return;
        }
        let propertyNames = Object.keys(geoJSON.features[0].properties);
        if(propertyNames.length < 1) {
            // We don't consider a GeoJSON file valid its features do not have properties
            this.alertInvalidFormat();
            return;
        }
        let selectedProperty = propertyNames[0];
        let newVal = {
            filename: file.name,
            geojson: geoJSON,
            modified: file.lastModifiedDate,
            properties: propertyNames,
            keyProperty: selectedProperty
        };
        this.setState({alertInvalidFormat: false}, () => {
            this.props.api.onParamChanged(this.props.paramId, {value: JSON.stringify(newVal)});
        });
    }

    onDrop = (acceptedFiles, rejectedFiles) => {
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
    };

    renderDropZoneContent() {
        if(this.state.isEmpty) {
            return (
                <div className={'map-upload-explainer'}>
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

        let propertyOptions = [];
        if(!this.state.isEmpty) {
            propertyOptions = this.state.properties.map((p) => {
                return (<option key={p} value={p} className={'dropdown-menu-item t-d-gray content-3'}>{p}</option>)
            });
        }

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
                {this.state.isEmpty ? '' : (
                    <div>
                        <div className='label-margin t-d-gray content-3'>Location property</div>
                        <select
                            className={'custom-select module-parameter dropdown-selector'}
                            name={'location'}
                            value={this.state.keyProperty}
                            disabled={this.props.isReadOnly}
                            onChange={this.handlePropertySelectionChange}
                        >
                            {propertyOptions}
                        </select>
                    </div>
                )}
            </div>
        );
    }
}