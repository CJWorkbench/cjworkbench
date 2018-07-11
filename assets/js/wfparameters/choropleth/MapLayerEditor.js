import React from 'react'
import PropTypes from 'prop-types'
import WorkbenchAPI from '../../WorkbenchAPI'

var api = WorkbenchAPI();

export default class MapLayerEditor extends React.Component {
    static propTypes = {
        paramId: PropTypes.number.isRequired,
        wfModuleId: PropTypes.number.isRequired,
        isReadOnly: PropTypes.bool.isRequired,
    };

    constructor(props) {
        super(props);

        this.state = {
            columns: []
        }
    }

    componentDidMount() {
        api.inputColumns(this.props.wfModuleId).then((result) => {
            console.log(result);
        });
    }

    render() {
        return (<div>This is a test</div>);
    }
}