import React from 'react';
import Choropleth from 'react-leaflet-choropleth'
import { Map, TileLayer, Marker, Popup } from 'react-leaflet'
import { store, wfModuleStatusAction } from '../../workflow-reducer'
import PropTypes from 'prop-types'
import { Form, FormGroup, Label, Input, Container, Row, Col } from 'reactstrap'
import { GithubPicker } from 'react-color'
import Color from 'color'

import 'leaflet/dist/leaflet.css'

export default class MapChart extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            lat: 37.8,
            lng: -96,
            zoom: 4,
            mapType: 'Select A Type',
            bounds: [[49.3457868, -124.7844079], [24.7433195, -66.9513812]],
            geoJSON: {},
            geoJSONAux: {},
            style: {},
            dataDict: {},
            dataColnames: [],
            mapFrame: <Map />,
            formColLoc: 'NULL',
            formColVal: 'NULL',
            geoJSONLoc: 'name',
            formSteps: 5,
            colorPickerStyle: {},
            colorScheme: '#1273DE',
        };
        this.state.style = {
            fillColor: "#f2f2f2",
            weight: 2,
            opacity: 1,
            color: 'white',
            dashArray: '3',
            fillOpacity: 0.7
        };
        console.log(props.loadState());
        this.handleChange = this.handleChange.bind(this);
        this.handleColorChange = this.handleColorChange.bind(this);
    }

    componentDidMount() {
        this.genTypeForm();
    }

    componentWillReceiveProps(nextProps) {
        if(this.props.revision != nextProps.revision) {
            this.loadData();
        }
    }

    loadData() {
        var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
        fetch(url, { credentials: 'include'})
            .then(response => response.json())
            .then(data => {
                var dataRows = data.rows;
                if(this.state.mapType == 'State') {
                    var newState = Object.assign({}, this.state);
                    if(newState.formColLoc == 'NULL') {
                        newState.formColLoc = data.columns[0];
                    }
                    if(newState.formColVal == 'NULL') {
                        newState.formColVal = data.columns[1];
                    }
                    var statesGeoJSON = require('./geojson/us-states.js').default;
                    var statesAbbr = require('./utils/states-abbr.js').default;
                    var dataDict = {};
                    for(var i = 0; i < dataRows.length; i ++) {
                        var ssign = dataRows[i][newState.formColLoc];
                        var sname = ssign;
                        if(ssign.length == 2) {
                            var sname = statesAbbr[ssign];
                        }
                        dataDict[sname] = dataRows[i][newState.formColVal];
                    }
                    newState.lat = 37.8;
                    newState.lng = -96;
                    newState.bounds = [[49.3457868, -124.7844079], [24.7433195, -66.9513812]];
                    newState.zoom = 4;
                    newState.geoJSON = Object.assign({}, statesGeoJSON);
                    newState.geoJSONAux = Object.assign({}, statesGeoJSON);
                    newState.dataDict = dataDict;
                    newState.dataColnames = data.columns;
                    newState.geoJSONLoc = 'name';
                    this.state = Object.assign({}, newState);
                    this.genMap();
                } else if(this.state.mapType == 'NYC Precinct') {
                    var newState = Object.assign({}, this.state);
                    if(newState.formColLoc == 'NULL') {
                        newState.formColLoc = data.columns[0];
                    }
                    if(newState.formColVal == 'NULL') {
                        newState.formColVal = data.columns[1];
                    }
                    var precinctGeoJSON = require('./geojson/nyc-precincts.js').default;
                    var dataDict = {};
                    for(var i = 0; i < dataRows.length; i ++) {
                        var loc = dataRows[i][newState.formColLoc];
                        if(loc != undefined) {
                            dataDict[loc.toString()] = dataRows[i][newState.formColVal];
                        }
                    }
                    newState.lat = 40.730610;
                    newState.lng = -73.935242;
                    newState.zoom = 10;
                    newState.bounds = [[40.917577, -73.700272], [40.477399, -74.259090]];
                    newState.geoJSON = precinctGeoJSON;
                    newState.dataDict = dataDict;
                    newState.dataColnames = data.columns;
                    newState.geoJSONLoc = 'Precinct';
                    this.state = Object.assign({}, newState);
                    this.genMap();
                }
            });
    }

    genMap() {
        console.log(this.state);
        const position = [this.state.lat, this.state.lng];
        var newMap = (
            <Container style={{width:"100%"}}>
                { this.genTypeForm() }
                <Row>
                    <Col xs={12}>
                        <h4>{this.state.formColVal}</h4>
                    </Col>
                </Row>
                <Row>
                    <Col xs={12}>
                        <Map center={position} zoom={this.state.zoom} style={{height:"300px"}}
                            bounds={this.state.bounds}>
                            <TileLayer
                                attribution='&copy; OpenStreetMap contributors'
                                url='http://{s}.tile.osm.org/{z}/{x}/{y}.png'
                            />
                            <Choropleth
                                data={{type: 'FeatureCollection', features: this.state.geoJSON.features}}
                                valueProperty={(feature) => this.state.dataDict[feature.properties[this.state.geoJSONLoc]]}
                                scale={[Color(this.state.colorScheme).lighten(0.7).rgbNumber(),
                                    Color(this.state.colorScheme).darken(0.7).rgbNumber()]}
                                steps={parseInt(this.state.formSteps)}
                                mode='q'
                                style={this.state.style}
                            />
                        </Map>
                    </Col>
                </Row>
                { this.genForm() }
            </Container>
        );
        console.log(newMap);
        this.setState({mapFrame: newMap});
    }

    genTypeForm() {
        return (
            <Form style={{"margin-top":"20px"}}>
                <FormGroup row>
                    <Col xs={12}>
                        <FormGroup>
                            <Label>Type of map</Label>
                            <Input type="select" value={this.state.mapType} name="mapType" onChange={this.handleChange}>
                                <option value="Select A Type" key={0} disabled>Select A Type</option>
                                <option value="State" key={1}>State</option>
                                <option value="NYC Precinct" key={2}>NYC Precinct</option>
                            </Input>
                        </FormGroup>
                    </Col>
                </FormGroup>
            </Form>
        );
    }

    genForm() {
        return (
            <Form style={{"margin-top":"20px"}}>
                <FormGroup row>
                    <Col xs={4}>
                        <FormGroup>
                            <Label>Location column</Label>
                            <Input type="select" value={this.state.formColLoc} name="formColLoc" onChange={this.handleChange}>
                                {this.state.dataColnames.map((cols, i) => <option value={cols} key={i}>{cols}</option>)}
                            </Input>
                        </FormGroup>
                    </Col>
                    <Col xs={4}>
                        <FormGroup>
                            <Label>Data column</Label>
                            <Input type="select" name="formColVal" value={this.state.formColVal} onChange={this.handleChange} >
                                {this.state.dataColnames.map((cols, i) => <option value={cols} key={i}>{cols}</option>)}
                            </Input>
                        </FormGroup>
                    </Col>
                    <Col xs={4}>
                        <FormGroup>
                            <Label># of levels</Label>
                            <Input type="select" name="formSteps" value={this.state.formSteps} onChange={this.handleChange} >
                                {[2, 3, 4, 5, 6, 7, 8, 9, 10].map((cols, i) => <option value={cols} key={i}>{cols}</option>)}
                            </Input>
                        </FormGroup>
                    </Col>
                </FormGroup>
                <FormGroup row>
                    <Col xs="12">
                        <FormGroup>
                            <Label>Color scheme</Label>
                            <GithubPicker
                                triangle="hide"
                                onChangeComplete={this.handleColorChange}
                                width="100%"
                                colors={['#B80000', '#DB3E00', '#FCCB00', '#008B02', '#006B76', '#1273DE', '#004DCF', '#5300EB', '#EB9694', '#FAD0C3', '#FEF3BD', '#C1E1C5', '#BEDADC', '#C4DEF6', '#BED3F3']}
                            />
                        </FormGroup>
                    </Col>
                </FormGroup>
            </Form>
        )
    }

    handleColorChange(color, event) {
        this.setState({
            colorScheme: color.hex
        }, this.loadData());
    }

    handleChange(event) {
        this.setState({
            [event.target.name]: event.target.value
        }, this.loadData());
    }

    render() {
        if(this.state.mapType != 'Select A Type') {
            return this.state.mapFrame;
        } else {
            return this.genTypeForm();
        }
    }
}
