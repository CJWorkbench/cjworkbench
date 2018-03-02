import React from 'react'
import PropTypes from 'prop-types'
import WorkbenchAPI from '../WorkbenchAPI'
import ReactDataGrid from 'react-data-grid'
import ColumnSelector from "./ColumnSelector"
//import {Form, FormGroup, Label, Input, FormText, Col, Table} from 'reactstrap'


var api = WorkbenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

const editColumns = [
    {
        key: 'column',
        name: 'Column',
        editable: false
    },
    {
        key: 'fromVal',
        name: 'From',
        editable: false
    },
    {
        key: 'toVal',
        name: 'To',
        editable: false
    }
];

class EditRow extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            initValue: this.props.dataValue,
            dataValue: this.props.dataValue,
            dataCount: this.props.dataCount,
            selected: this.props.valueSelected,
        }
        this.handleValueChange = this.handleValueChange.bind(this);
        this.handleBlur = this.handleBlur.bind(this);
        this.handleFocus = this.handleFocus.bind(this);
        this.handleKeyPress = this.handleKeyPress.bind(this);

        this.handleSelectionChange = this.handleSelectionChange.bind(this);
    }

    handleValueChange(event) {
        var nextState = Object.assign({}, this.state);
        nextState.dataValue = event.target.value;
        this.setState(nextState);
    }

    handleKeyPress(event) {
        if(event.key == 'Enter') {
            event.preventDefault();
            this.sendValueChange();
        }
    }

    handleBlur() {
        this.sendValueChange();
    }

    sendValueChange() {
        this.props.onValueChange({
            fromVal: this.state.initValue,
            toVal: this.state.dataValue
        });
    }

    handleFocus(event) {
        console.log('focused');
        event.target.select();
    }

    handleSelectionChange(event) {
        var nextState = Object.assign({}, this.state);
        nextState.selected = (!nextState.selected);
        this.setState(nextState);
        this.props.onSelectionChange({
            value: this.state.initValue
        });
    }

    render() {
        return (
            <div className='checkbox-container' style={{'whiteSpace': 'nowrap'}}>
                <input
                    type='checkbox'
                    onChange={this.handleSelectionChange}
                    checked={this.state.selected}
                />
                <span className='ml-3 t-d-gray checkbox-content content-3'>
                    <input
                        type='text'
                        value={this.state.dataValue}
                        onChange={this.handleValueChange}
                        onFocus={this.handleFocus}
                        onBlur={this.handleBlur}
                        onClick={this.handleClick}
                        onKeyPress={this.handleKeyPress}
                        style={{'width': '130px'}}
                    />
                </span>
                <span className='ml-3 t-d-gray checkbox-content content-3'>{this.state.dataCount}</span>
            </div>
        )
    }
};

export default class Refine extends React.Component {

    /*
    Format of edits:
    {
        type: 'select' or 'change',
        column: target column
        content: {
            fromVal: ...(for 'change')
            toVal: ...(for 'change')
            value: ...(for 'select')
        },
        timestamp: ...
    }
     */

    constructor(props) {
        super(props);
        this.state = {
            histogramLoaded: false,
            histogramData: [],
            histogramNumRows: 0,
            histogramColumns: [],
            edits: JSON.parse(props.existingEdits.length > 0 ? props.existingEdits : '[]'),
        }
        this.rowGetter = this.rowGetter.bind(this);
        this.handleGridRowsUpdated = this.handleGridRowsUpdated.bind(this);

        this.editsRowGetter = this.editsRowGetter.bind(this);

        this.handleValueChange = this.handleValueChange.bind(this);
        this.handleSelectionChange = this.handleSelectionChange.bind(this);

        console.log(this.state.edits);
    }

    componentDidMount() {
        this.loadHistogram(this.props.selectedColumn);
    }

    componentWillReceiveProps(nextProps) {
        var nextColumn = nextProps.selectedColumn;
        var nextRevision = nextProps.revision;
        if(nextRevision != this.props.revision) {
            //console.log('Revision bumped.');
            this.setState({
                histogramLoaded: false,
                histogramData: [],
                histogramNumRows: 0,
                histogramColumns: [],
                edits: JSON.parse(nextProps.existingEdits.length > 0 ? nextProps.existingEdits : '[]'),
            });
            this.loadHistogram(nextColumn);
        }
    }

    loadHistogram(targetCol) {
        api.histogram(this.props.wfModuleId, targetCol)
            .then(histogram => {
                var nextState = Object.assign({}, this.state);
                var editedHistogram = histogram.rows.map(function(entry) {
                    var newEntry = Object.assign({}, entry);
                    newEntry.selected = true;
                    return newEntry;
                });
                console.log(editedHistogram);
                // Apply all relevant edits we have to the original histogram
                for(var i = 0; i < this.state.edits.length; i ++) {
                    if(this.state.edits[i].column == this.props.selectedColumn) {
                        editedHistogram = this.applySingleEdit(editedHistogram, this.state.edits[i]);
                    }
                }
                nextState.histogramData = editedHistogram;
                nextState.histogramNumRows = editedHistogram.length;
                nextState.histogramLoaded = true;
                nextState.histogramColumns = histogram.columns.map(cname => ({key: cname, name: cname, editable: !(cname == 'count')}));
                this.setState(nextState);
                console.log(nextState.histogramData);
            });
    }

    applySingleEdit(hist, edit) {
        console.log(edit);
        var newHist = hist.slice();
        if(edit.type == 'change') {
            var fromIdx = newHist.findIndex(function(element) {
               return (element[edit.column] == edit.content.fromVal);
            });
            var fromEntry = Object.assign({}, newHist[fromIdx]);
            newHist.splice(fromIdx, 1);
            var toIdx = newHist.findIndex(function(element) {
                return (element[edit.column] == edit.content.toVal);
            });
            if (toIdx == -1) {
                // If no "to" entry was found, create a new entry
                var newEntry = Object.assign({}, fromEntry);
                newEntry[edit.column] = edit.content.toVal;
                newHist.unshift(newEntry);
            } else {
                // Otherwise, we merge the "from" entry to the "to" entry
                // The new cluster always appears on top
                var toEntry = Object.assign({}, newHist[toIdx]);
                newHist.splice(toIdx, 1);
                toEntry['count'] += fromEntry['count'];
                newHist.unshift(toEntry);
            }
        } else if(edit.type == 'select') {
            var targetIdx = newHist.findIndex(function(element) {
               return (element[edit.column] == edit.content.value);
            });
            newHist[targetIdx].selected = (!newHist[targetIdx].selected);
        }
        return newHist;
    }

    rowGetter(i) {
        return this.state.histogramData[i];
    };

    editsRowGetter(i) {
        return this.state.edits[this.state.edits.length - i - 1];
    }

    handleGridRowsUpdated(data) {
        console.log(data);
        var changeCol = data.cellKey;
        if(changeCol == 'count') {
            return;
        }
        var fromVal = data.fromRowData[changeCol];
        var toVal = data.updated[changeCol];
        if(fromVal == toVal) {
            return;
        }
        var nextEdits = this.state.edits.slice()
        nextEdits.push({
            column: changeCol,
            fromVal: fromVal,
            toVal: toVal,
            timestamp: Date.now()
        });
        this.props.saveEdits(JSON.stringify(nextEdits));
    }

    handleValueChange(changeData) {
        console.log('Value changed');
        console.log(changeData);
        var nextEdits = this.state.edits.slice();
        nextEdits.push({
            type: 'change',
            column: this.props.selectedColumn,
            content: {
                fromVal: changeData.fromVal,
                toVal: changeData.toVal
            },
            timestamp: Date.now()
        });
        console.log(nextEdits);
        this.props.saveEdits(JSON.stringify(nextEdits));
    }

    handleSelectionChange(changeData) {
        console.log(changeData);
        var nextEdits = this.state.edits.slice();
        nextEdits.push({
            type: 'select',
            column: this.props.selectedColumn,
            content: {
                value: changeData.value,
            },
            timestamp: Date.now()
        });
        console.log(nextEdits);
        this.props.saveEdits(JSON.stringify(nextEdits));
    }

    renderHistogram() {
        if(this.state.histogramLoaded) {
            return (
                <div>
                    <div className='t-d-gray content-3 label-margin'>Histogram</div>
                    <ReactDataGrid
                        enableCellSelect={true}
                        columns={this.state.histogramColumns}
                        rowGetter={this.rowGetter}
                        rowsCount={this.state.histogramNumRows}
                        minHeight={350}
                        rowHeight={35}
                        onGridRowsUpdated={this.handleGridRowsUpdated}
                    />
                </div>
            )
        }
        return (<div>Loading data...</div>);
    }

    renderHistogramNew() {
        if(this.state.histogramLoaded) {
            const checkboxes = this.state.histogramData.map(item => {
                return (
                    <EditRow
                        dataValue={item[this.props.selectedColumn]}
                        dataCount={item.count}
                        key={item[this.props.selectedColumn]}
                        onValueChange={this.handleValueChange}
                        onSelectionChange={this.handleSelectionChange}
                        valueSelected={item.selected}
                    />
                );
            });

            //console.log(checkboxes);

            return (
                <div>
                    <div className='t-d-gray content-3 label-margin'>Histogram</div>
                    <div className='container list-wrapper' style={{'height': '400px'}}>
                        <div className='row list-scroll'>
                            { checkboxes }
                        </div>
                    </div>
                </div>
            )
        }
    }

    renderEdits() {
        if(this.state.edits.length > 0) {
            return (
                <div>
                    <div className='t-d-gray content-3 label-margin'>Edits</div>
                    <ReactDataGrid
                        columns={editColumns}
                        rowGetter={this.editsRowGetter}
                        rowsCount={this.state.edits.length}
                        minHeight={350}
                        rowHeight={35}
                    />
                </div>
            )
        }
        return (<div>No edits yet.</div>)
    }

    render() {
        const histogramDatagrid = this.renderHistogramNew();
        const editsDatagrid = this.renderEdits();
        return (
            <div>
                {histogramDatagrid}
                <br />
            </div>
        )
    }
};

Refine.propTypes = {
  wfModuleId: PropTypes.number.isRequired,
  selectedColumn: PropTypes.string.isRequired,
  existingEdits: PropTypes.string.isRequired,
  saveEdits: PropTypes.func.isRequired,
  revision: PropTypes.number.isRequired
};