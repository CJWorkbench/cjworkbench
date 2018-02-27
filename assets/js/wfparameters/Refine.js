import React from 'react';
import PropTypes from 'prop-types'
import WorkbenchAPI from '../WorkbenchAPI'
import ReactDataGrid from 'react-data-grid'


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

export default class Refine extends React.Component {

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
    }

    componentDidMount() {
        this.loadHistogram(this.props.selectedColumn);
    }

    componentWillReceiveProps(nextProps) {
        var nextColumn = nextProps.selectedColumn;
        var nextRevision = nextProps.revision;
        if(nextRevision != this.props.revision) {
            console.log('Revision bumped.');
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
                var editedHistogram = histogram.rows.slice();
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
        var fromIdx = -1;
        for(var i = 0; i < newHist.length; i ++) {
            if(newHist[i][edit.column] == edit.fromVal) {
                fromIdx = i;
                break;
            }
        }
        var fromEntry = Object.assign({}, newHist[fromIdx]);
        newHist.splice(fromIdx, 1);
        var toIdx = -1;
        for(var i = 0; i < newHist.length; i ++) {
            if(newHist[i][edit.column] == edit.toVal) {
                toIdx = i;
                break;
            }
        }
        if(toIdx == -1) {
            // If no "to" entry was found, create a new entry
            var newEntry = {};
            newEntry[edit.column] = edit.toVal;
            newEntry['count'] = fromEntry.count;
            newHist.unshift(newEntry);
        } else {
            // Otherwise, we merge the "from" entry to the "to" entry
            // The delete -> unshift approach is used to deal with a bug in DataGrid's refreshing
            var toEntry = Object.assign({}, newHist[toIdx]);
            newHist.splice(toIdx, 1);
            toEntry['count'] += fromEntry['count'];
            newHist.unshift(toEntry);
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
        const histogramDatagrid = this.renderHistogram();
        const editsDatagrid = this.renderEdits();
        return (
            <div>
                {histogramDatagrid}
                <br />
                {editsDatagrid}
                <br/>
            </div>
        )
    }
};