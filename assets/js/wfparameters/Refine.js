import React from 'react';
import PropTypes from 'prop-types'
import WorkbenchAPI from '../WorkbenchAPI'
import ReactDataGrid from 'react-data-grid'
import {Form, FormGroup, Label, Input} from 'reactstrap';
import {changeParamAction, store} from '../workflow-reducer'


var api = WorkbenchAPI();
export function mockAPI(mock_api) {
    api = mock_api;
}

export default class Refine extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            histogramLoaded: false,
            histogram: [],
            histogramColumns: [],
        }
        this.rowGetter = this.rowGetter.bind(this);
    }

    componentDidMount() {
        this.loadHistogram(this.props.selectedColumn);
    }

    componentWillReceiveProps(nextProps) {
        var nextColumn = nextProps.selectedColumn;
        if(nextColumn != this.props.selectedColumn) {
            this.loadHistogram(nextColumn);
        }
    }

    loadHistogram(targetCol) {
        api.histogram(this.props.wfModuleId, targetCol)
            .then(histogram => {
                var nextState = Object.assign({}, this.state);
                nextState.histogram = histogram;
                nextState.histogramLoaded = true;
                nextState.histogramColumns = histogram.columns.map(cname => ({key: cname, name: cname, editable: !(cname == 'count')}));
                this.setState(nextState);
                //this.props.saveCurrentColumn(target_col);
            });
    }

    rowGetter(i) {
        return this.state.histogram.rows[i];
    };

    renderHistogram() {
        if(this.state.histogramLoaded) {
            return (
                <ReactDataGrid
                    enableCellSelect={true}
                    columns={this.state.histogramColumns}
                    rowGetter={this.rowGetter}
                    rowsCount={this.state.histogram.total_rows}
                    minHeight={350}
                    rowHeight={35}
                />
            )
        }
        return (<div>Loading data...</div>);
    }

    render() {
        const histogramDatagrid = this.renderHistogram();
        return (
            <div>
                {histogramDatagrid}
                <br />
            </div>
        )
    }
};