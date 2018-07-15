import React from 'react'
import PropTypes from 'prop-types'
import WorkbenchAPI from '../../WorkbenchAPI'

var api = WorkbenchAPI();

export default class MapTokenSelector extends React.Component {
    static propTypes = {
        name: PropTypes.string.isRequired,
        paramId: PropTypes.number.isRequired,
        paramData: PropTypes.string.isRequired,
        isReadOnly: PropTypes.bool.isRequired
    };


    constructor(props) {
        super(props);

        // Mapbox does not require the default token to be kept secret; this is the default token
        // of my personal account
        this.defaultToken = 'pk.eyJ1IjoiaGFycnktdGMtemhhbmciLCJhIjoiY2ppeDhoZ3d2MGUxYjNrcGRxdzlwZ2g0aSJ9.JphK_2HqLSJ1GR3Fpkugag';

        this.state = Object.assign({}, this.parsePropsToState(props.paramData));
        console.log(this.state);
    }

    componentDidMount() {
        console.log(this.state);

        // We load the default token when the module first loads
        if(this.state.isInitialLoad) {
            api.onParamChanged(this.props.paramId, {value: JSON.stringify({
                    sourceVal: this.state.sourceVal,
                    tokenVal: this.state.tokenVal,
                    isInitialLoad: false
                })});
        }
    }

    componentWillReceiveProps(nextProps) {
        if(nextProps.paramData != this.props.paramData) {
            this.setState(this.parsePropsToState(nextProps.paramData));
        }
    }

    parsePropsToState(paramData) {
        console.log(paramData);
        let paramVal = {};
        // isInitialLoad is only true upon the initial load, when paramData is empty
        let isInitialLoad = false;
        try {
            paramVal = JSON.parse(paramData);
        } catch(e) {
            isInitialLoad = true;
        }

        console.log(paramVal);
        return {
            sourceVal: isInitialLoad ? 'default' : paramVal.sourceVal,
            tokenVal: paramVal.tokenVal ? paramVal.tokenVal : this.defaultToken,
            isInitialLoad: isInitialLoad
        }
    }

    updateParamOnServer(paramData) {
        api.onParamChanged(this.props.paramId, {value: JSON.stringify(paramData)});
    }

    onSourceChange = (e) => {
        let val = e.target.value;
        let nextToken = (val == 'default') ? this.defaultToken : this.tokenVal;
        this.setState({
            sourceVal: val,
            tokenVal: nextToken
        }, () => {
            this.updateParamOnServer(this.state);
        });
    };

    onInputBlur = (e) => {
        var tokenVal = e.target.value;
        this.setState({tokenVal: tokenVal}, () => {
            this.updateParamOnServer(this.state);
        });
    };

    onInputKeyPress = (e) => {
        if(e.key == 'Enter') {
            var tokenVal = e.target.value;
            this.setState({tokenVal: tokenVal}, () => {
                this.updateParamOnServer(this.state);
            });
        }
    };

    onInputFocus = (e) => {
        this.stringRef.select();
    };

    onInputChange = (e) => {
        this.setState({
            tokenVal: e.target.value
        });
    };

    renderTokenInput() {
        if(this.state.sourceVal == 'default') {
            return '';
        }
        return (
            <div>
                <div className='label-margin t-d-gray content-3'>{this.props.name}</div>
                <textarea
                    onBlur={this.onInputBlur}
                    onKeyPress={this.onInputKeyPress}
                    onFocus={this.onInputFocus}
                    onChange={this.onInputChange}
                    readOnly={this.props.isReadOnly}
                    className={'module-parameter t-d-gray content-3 text-field-large'}
                    value={this.state.tokenVal}
                    rows={4}
                    ref={(el) => {this.stringRef = el}}
                />
            </div>
        )
    }

    render() {
        return (
            <div>
                <div className='label-margin t-d-gray content-3'>{this.props.name}</div>
                <select
                    className={'custom-select module-parameter dropdown-selector'}
                    value={this.state.sourceVal}
                    onChange={this.onSourceChange}
                    disabled={this.props.isReadOnly}
                >
                    <option key={'map-default'} value={'default'}>Default</option>
                    <option key={'map-custom'} value={'custom'}>Use my own API token</option>
                </select>
                {this.renderTokenInput()}
            </div>
        )
    }
}