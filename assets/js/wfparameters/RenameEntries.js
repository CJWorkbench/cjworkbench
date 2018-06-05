import React from 'react'
import PropTypes from 'prop-types'
import WorkBenchAPI from '../WorkbenchAPI'

var api = WorkBenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

class RenameEntry extends React.Component {
    static propTypes = {
        colname: PropTypes.string.isRequired,
        newColname: PropTypes.string.isRequired,
        onColRename: PropTypes.func.isRequired
    };

    constructor(props) {
        super(props);

        this.handleChange = this.handleChange.bind(this);
    }

    handleChange(event) {
        this.props.onColRename(this.props.colname, event.target.value);
    }

    render() {
        return (
            <div>
                <div style={{width: '50%', float: 'left'}}>{this.props.colname}</div>
                <input
                    type={'text'}
                    value={this.props.newColname}
                    onChange={this.handleChange}
                />
            </div>
        )
    }
}

export default class RenameEntries extends React.Component {
    static propTypes = {
        displayAll: PropTypes.bool.isRequired,
        entries: PropTypes.string.isRequired,
        wfModuleId: PropTypes.number.isRequired,
        revision: PropTypes.number,
        paramId: PropTypes.number.isRequired,
    };

    constructor(props) {
        super(props);

        var entries = {}
        try {
            entries = JSON.parse(this.props.entries);
        } catch(e) {}

        this.state = {
            columns: undefined,
            entries: entries,
        }

        this.onInputBlur = this.onInputBlur.bind(this);
        this.onColRename = this.onColRename.bind(this);
    }

    refreshColumns() {
        api.inputColumns(this.props.wfModuleId)
            .then((columns) => {
                this.setState({columns: columns});
            });
    }

    componentWillReceiveProps(nextProps) {
        if(nextProps.entries != this.props.entries) {
            try {
                let newEntries = JSON.parse(nextProps.entries);
                this.setState({entries: newEntries});
            } catch(e) {
                this.setState({entries: {}});
            }
        }
        if(nextProps.revision != this.props.revision) {
            this.refreshColumns();
        }
    }

    componentDidMount() {
        this.refreshColumns();
    }

    onInputBlur(event) {
        console.log(event);
    }

    onColRename(prevName, nextName) {
        var newEntries = Object.assign({}, this.state.entries);
        newEntries[prevName] = nextName;
        console.log(newEntries);
        api.onParamChanged(this.props.paramId, {value: JSON.stringify(newEntries)});
    }

    renderEntries() {
        if(this.state.columns) {
            return this.state.columns.map((col) => {
                if(col in this.state.entries) {
                    return <RenameEntry key={col} colname={col} newColname={this.state.entries[col]} onColRename={this.onColRename}/>;
                } else {
                    return <RenameEntry key={col} colname={col} newColname={col} onColRename={this.onColRename}/>;
                }
            });
        } else {
            for(let col in this.state.entries) {
                return <RenameEntry key={col} colname={col} newColname={this.state.entries[col]} onColRename={this.onColRename}/>;
            }
        }
    }

    render() {
        const entries = this.renderEntries();
        return (
            <div>{entries}</div>
        )
    }
}