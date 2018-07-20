import React from 'react'
import PropTypes from 'prop-types'
import WorkbenchAPI from '../../WorkbenchAPI'

var api = WorkbenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

export default class MapLocationPresets extends React.Component {
    static propTypes = {
        paramData: PropTypes.string.isRequired,
        paramId: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        isReadOnly: PropTypes.bool.isRequired,
    };

    constructor(props) {
        super(props);

        this.state = this.parseParamData(props.paramData);
    }

    parseParamData(paramData) {
        let data = {};
        try {
            data = JSON.parse(paramData);
            return data;
        } catch(e) {
            return {
                preset: 'select',
                geojson: {}
            }
        }
    }

    onPresetSelectionChange = (event) => {
        let newPreset = event.target.value;
        this.setState({preset: event.target.value}, () => {
            let geoJSON = {};
            if(newPreset !== 'select') {
                geoJSON = require('./geojson/' + newPreset).default;
                api.onParamChanged(this.props.paramId, {value: JSON.stringify({
                    preset: newPreset,
                    geojson: geoJSON
                })});
            } else {
                api.onParamChanged(this.props.paramId, {value: ''});
            }
        });
    };

    render() {
        /*
            Preset format: array of {<filename>, <display name>}
            The filename must match the filenames (minus the extension) in the ./geojson directory
            To add a preset: wrap a geojson variable in "export default <geojson>;"
            and save as a .js file under the ./geojson directory, then update here.
         */
        const presets = [
            {filename: 'us-states', display: 'US States'},
            {filename: 'nyc-precincts', display: 'NYC precincts'}
        ];
        const presetOptions = presets.map((p) => {
            return (
                <option
                    key={p.filename}
                    value={p.filename}
                    className={'dropdown-menu-item t-d-gray content-3'}
                >
                    {p.display}
                </option>
            )
        });

        return (
            <div>
                <div className='label-margin t-d-gray content-3'>{this.props.name}</div>
                <select
                    className={'custom-select module-parameter dropdown-selector'}
                    name={this.props.name}
                    value={this.state.preset}
                    onChange={this.onPresetSelectionChange}
                    disabled={this.props.isReadOnly}
                >
                    <option key={'select'} value={'select'} className={'dropdown-menu-item t-d-gray content-3'}>Select</option>
                    {presetOptions}
                </select>
            </div>
        )
    }
}