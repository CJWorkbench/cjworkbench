import React from 'react'
import PropTypes from 'prop-types'
import WorkbenchAPI from '../WorkbenchAPI'
//import {Form, FormGroup, Label, Input, FormText, Col, Table} from 'reactstrap'
import {UncontrolledAlert} from 'reactstrap'


var api = WorkbenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

const INTERNAL_COUNT_COLNAME = '__internal_count_column__'

class EditRow extends React.Component {

    // Component for each row in the histogram

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

    componentWillReceiveProps(nextProps) {
        var nextState = Object.assign({}, this.state);
        nextState.initValue = nextProps.dataValue;
        nextState.dataValue = nextProps.dataValue;
        nextState.dataCount = nextProps.dataCount;
        nextState.selected = nextProps.valueSelected;
        this.setState(nextState);
    }

    handleValueChange(event) {
        var nextState = Object.assign({}, this.state);
        nextState.dataValue = event.target.value;
        this.setState(nextState);
    }

    handleKeyPress(event) {
        if(event.key == 'Enter') {
            event.preventDefault();
            if(this.state.initValue != this.state.dataValue) {
                this.sendValueChange();
            }
        }
    }

    handleBlur() {
        if(this.state.initValue != this.state.dataValue) {
            this.sendValueChange();
        }
    }

    sendValueChange() {
        this.props.onValueChange({
            fromVal: this.state.initValue,
            toVal: this.state.dataValue
        });
    }

    handleFocus(event) {
        event.target.select();
    }

    handleSelectionChange(event) {
        //console.log('checkbox', event);
        var nextState = Object.assign({}, this.state);
        nextState.selected = (!nextState.selected);
        this.setState(nextState);
        this.props.onSelectionChange({
            value: this.state.initValue
        });
    }

    render() {
        return (
            <div
                className={'checkbox-container facet-checkbox-container ' + (this.props.valueEdited ? 'facet-edited' : '')}
                style={{'whiteSpace': 'nowrap'}}>
                <div className="d-flex align-items-center">
                  <input
                      type='checkbox'
                      onChange={this.handleSelectionChange}
                      checked={this.state.selected}
                      className={'facet-checkbox'}
                  />
                  <input
                      type='text'
                      value={this.state.dataValue}
                      onChange={this.handleValueChange}
                      onFocus={this.handleFocus}
                      onBlur={this.handleBlur}
                      onKeyPress={this.handleKeyPress}
                      className={'facet-value t-d-gray content-3' + (this.props.valueEdited ? ' facet-value--edited' : '')}
                  />
                </div>
                <div className='facet-count t-m-gray content-4'>{this.state.dataCount}</div>
            </div>
        )
    }
};

EditRow.propTypes = {
    dataValue: PropTypes.string.isRequired,
    dataCount: PropTypes.number.isRequired,
    onValueChange: PropTypes.func.isRequired,
    onSelectionChange: PropTypes.func.isRequired,
    valueSelected: PropTypes.bool.isRequired,
    valueEdited: PropTypes.bool.isRequired
}

export default class facet extends React.Component {

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
            showWarning: false,
            edits: JSON.parse(props.existingEdits.length > 0 ? props.existingEdits : '[]'),
        }

        this.handleValueChange = this.handleValueChange.bind(this);
        this.handleSelectionChange = this.handleSelectionChange.bind(this);

        //console.log(this.state.edits);
    }

    componentDidMount() {
        if(this.props.selectedColumn.length > 0) {
            this.loadHistogram(this.props.selectedColumn, this.state);
        }
    }

    componentWillReceiveProps(nextProps) {
        // Handles revision changes and column changes

        //console.log(nextProps);
        var nextColumn = nextProps.selectedColumn;
        var nextRevision = nextProps.revision;
        if(nextRevision != this.props.revision) {
            //console.log(nextRevision, this.props.revision);
            //console.log('Revision bumped.');
            if(nextColumn != this.props.selectedColumn) {
                // If the column changes, check if this is a undo; if not, clear the edits
                // The empty edits will be saved to the server on the next edit
                var nextState = Object.assign({}, this.state);
                nextState.showWarning = (nextRevision > this.props.revision) && (this.props.selectedColumn.length > 0);
                nextState.edits = (nextRevision > this.props.revision) ? [] : JSON.parse(nextProps.existingEdits);
                this.loadHistogram(nextColumn, nextState);

            } else {
                // Otherwise, load everything as usual
                var nextState = Object.assign({}, this.state);
                nextState.edits = JSON.parse(nextProps.existingEdits.length > 0 ? nextProps.existingEdits : '[]');
                nextState.showWarning = false;
                //console.log(nextState.edits);
                this.loadHistogram(nextColumn, nextState);
            }
        }
    }

    shouldComponentUpdate(nextProps, nextState) {
        // Prevents an extra rendering during a column change
        if((nextProps.selectedColumn != this.props.selectedColumn)) {
            return false;
        }
        return true;
    }

    loadHistogram(targetCol, baseState, clearEdits=false) {
        // Loads a histogram from the server and sets the state with the result

        // clearEdits controls whether we clear the edit on the server immediately upon load
        // This is unused for now.
        api.histogram(this.props.wfModuleId, targetCol)
            .then(histogram => {
                //console.log(histogram);
                var nextState = Object.assign({}, baseState);
                var editedHistogram = histogram.rows.map(function(entry) {
                    var newEntry = Object.assign({}, entry);
                    newEntry.selected = true;
                    newEntry.edited = false;
                    return newEntry;
                });
                //console.log(this.state.edits);
                //console.log(editedHistogram);
                // Apply all relevant edits we have to the original histogram
                //console.log(nextState.edits);
                for(var i = 0; i < nextState.edits.length; i ++) {
                    //console.log('applying edit');
                    if(nextState.edits[i].column == this.props.selectedColumn) {
                        //console.log('applying edit');
                        editedHistogram = this.applySingleEdit(editedHistogram, nextState.edits[i]);
                    }
                }
                //console.log(editedHistogram);
                editedHistogram.sort((item1, item2) => {
                    return item1[INTERNAL_COUNT_COLNAME] < item2[INTERNAL_COUNT_COLNAME] ? 1 : -1;
                })
                nextState.histogramData = editedHistogram;
                nextState.histogramNumRows = editedHistogram.length;
                nextState.histogramLoaded = true;
                this.setState(nextState);
                //console.log(nextState.histogramData);
            })
            .then(() => {
                if(clearEdits) {
                    this.props.saveEdits('[]');
                }
            });
    }

    applySingleEdit(hist, edit) {
        // Applies edits on the client side

        //console.log(edit);
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
                newEntry.edited = true;
                newHist.unshift(newEntry);
            } else {
                // Otherwise, we merge the "from" entry to the "to" entry
                // The new cluster always appears on top
                var toEntry = Object.assign({}, newHist[toIdx]);
                newHist.splice(toIdx, 1);
                toEntry[INTERNAL_COUNT_COLNAME] += fromEntry[INTERNAL_COUNT_COLNAME];
                toEntry.edited = true;
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

    handleValueChange(changeData) {
        // Handles edits to values; pushes changes to the server by setting the parameter

        //console.log('Value changed');
        //console.log(changeData);
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
        //console.log(nextEdits);
        this.props.saveEdits(JSON.stringify(nextEdits));
    }

    handleSelectionChange(changeData) {
        // Handles selection/deselection of facets; pushes changes to server

        //console.log(changeData);
        var nextEdits = this.state.edits.slice();
        nextEdits.push({
            type: 'select',
            column: this.props.selectedColumn,
            content: {
                value: changeData.value,
            },
            timestamp: Date.now()
        });
        //console.log(nextEdits);
        this.props.saveEdits(JSON.stringify(nextEdits));
    }

    renderHistogram() {
        if(this.state.histogramLoaded) {
            const checkboxes = this.state.histogramData.map(item => {
                return (
                    <EditRow
                        dataValue={item[this.props.selectedColumn].toString()}
                        dataCount={item[INTERNAL_COUNT_COLNAME]}
                        key={item[this.props.selectedColumn]}
                        onValueChange={this.handleValueChange}
                        onSelectionChange={this.handleSelectionChange}
                        valueSelected={item.selected}
                        valueEdited={item.edited}
                    />
                );
            });

            //console.log(checkboxes);

            return (
                <div>
                    {this.state.showWarning ?
                        (<UncontrolledAlert color={'warning'}>
                            Switching columns will clear your previous work. If you did it by accident, use "undo" from the top-right menu to go back,
                        </UncontrolledAlert>) : ''
                    }
                    <div className='t-d-gray content-3 label-margin'>Histogram</div>
                    <div className='container list-wrapper'>
                        <div className='row list-scroll'>
                            { checkboxes }
                        </div>
                    </div>
                </div>
            )
        }
    }

    render() {
        const histogramComponent = this.renderHistogram();
        return (
            <div>
                {histogramComponent}
                <br />
            </div>
        )
    }
};

facet.propTypes = {
    wfModuleId: PropTypes.number.isRequired,
    selectedColumn: PropTypes.string.isRequired,
    existingEdits: PropTypes.string.isRequired,
    saveEdits: PropTypes.func.isRequired,
    revision: PropTypes.number.isRequired
};
