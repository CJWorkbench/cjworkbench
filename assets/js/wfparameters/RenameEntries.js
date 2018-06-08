import React from 'react'
import PropTypes from 'prop-types'
import WorkBenchAPI from '../WorkbenchAPI'

var api = WorkBenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

export class RenameEntry extends React.Component {
    static propTypes = {
        colname: PropTypes.string.isRequired,
        newColname: PropTypes.string.isRequired,
        onColRename: PropTypes.func.isRequired,
        onEntryDelete: PropTypes.func.isRequired,
    };

    constructor(props) {
        super(props);

        this.state = {
            inputValue: this.props.newColname
        };

        this.handleChange = this.handleChange.bind(this);
        this.handleKeyPress = this.handleKeyPress.bind(this);
        this.handleBlur = this.handleBlur.bind(this);
        this.handleFocus = this.handleFocus.bind(this);
        this.handleDelete = this.handleDelete.bind(this);
    }

    componentWillReceiveProps(nextProps) {
        if(nextProps.newColname != this.state.inputValue) {
            this.setState({inputValue: nextProps.newColname});
        }
    }

    handleChange(event) {
        //this.props.onColRename(this.props.colname, event.target.value);
        this.setState({inputValue: event.target.value});
    }

    handleBlur() {
        if(this.state.inputValue != this.props.newColname) {
            this.props.onColRename(this.props.colname, this.state.inputValue);
        }
    }

    handleKeyPress(event) {
        if((event.key == 'Enter') && (this.state.inputValue != this.props.newColname)) {
            this.props.onColRename(this.props.colname, this.state.inputValue);
        }
    }

    handleFocus(event) {
        event.target.select();
    }

    handleDelete() {
        this.props.onEntryDelete(this.props.colname);
    }

    render() {
        // The class names below are used in testing.
        // Changing them would require updating the tests accordingly.
        return (
            <div>
                <div className={'rename-column'} style={{width: '40%', float: 'left'}}>{this.props.colname}</div>
                <input
                    className={'rename-input'}
                    style={{width: '50%'}}
                    type={'text'}
                    value={this.state.inputValue}
                    onChange={this.handleChange}
                    onBlur={this.handleBlur}
                    onKeyPress={this.handleKeyPress}
                    onFocus={this.handleFocus}
                />
                <button className={'rename-delete'} onClick={this.handleDelete}>X</button>
            </div>
        )
    }
}

export default class RenameEntries extends React.Component {
    static propTypes = {
        loadAll: PropTypes.bool.isRequired,
        changeLoadAll: PropTypes.func.isRequired,
        entries: PropTypes.string.isRequired,
        wfModuleId: PropTypes.number.isRequired,
        revision: PropTypes.number,
        paramId: PropTypes.number.isRequired,
    };

    constructor(props) {
        super(props);

        var entries = {};
        try {
            entries = JSON.parse(this.props.entries);
        } catch(e) {}

        this.state = {
            columns: undefined,
            entries: entries,
        };

        this.onColRename = this.onColRename.bind(this);
        this.onEntryDelete = this.onEntryDelete.bind(this);
    }

    refreshColumns(props) {
        if(props.loadAll) {
            api.inputColumns(props.wfModuleId)
                .then((columns) => {
                    this.setState({columns: columns});
                });
        } else {
            this.setState({columns: undefined});
        }
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
        if((nextProps.revision != this.props.revision) || (nextProps.loadAll != this.props.loadAll)) {
            this.refreshColumns(nextProps);
        }
    }

    componentDidMount() {
        //this.refreshColumns(this.props);
        if(this.props.loadAll) {
            api.inputColumns(this.props.wfModuleId)
                .then((columns) => {
                    var entries = {};
                    for(var idx in columns) {
                        entries[columns[idx]] = columns[idx];
                    }
                    api.onParamChanged(this.props.paramId, {value: JSON.stringify(entries)})
                        .then(() => {
                            this.props.changeLoadAll(false);
                        })
                });
        }
    }

    onColRename(prevName, nextName) {
        var newEntries = Object.assign({}, this.state.entries);
        newEntries[prevName] = nextName;
        api.onParamChanged(this.props.paramId, {value: JSON.stringify(newEntries)});
    }

    onEntryDelete(prevName) {
        var newEntries = Object.assign({}, this.state.entries);
        if(prevName in newEntries) {
            delete newEntries[prevName];
            if(Object.keys(newEntries).length == 0) {
                api.deleteModule(this.props.wfModuleId);
            } else {
                api.onParamChanged(this.props.paramId, {value: JSON.stringify(newEntries)});
            }
        }
    }

    renderEntries() {
        var entries = [];
        for(let col in this.state.entries) {
            entries.push(
                <RenameEntry
                    key={col}
                    colname={col}
                    newColname={this.state.entries[col]}
                    onColRename={this.onColRename}
                    onEntryDelete={this.onEntryDelete}
                />
            );
        }
        return entries;
    }

    render() {
        const entries = this.renderEntries();
        return (
            <div>{entries}</div>
        )
    }
}