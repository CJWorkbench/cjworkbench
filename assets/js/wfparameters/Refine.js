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
            histogram_loaded: false,
            histogram: [],
            histogram_columns: [],
            current_column: 'colplaceholder',
            columns_loaded: false,
            columns: []
        }
        this.handleColumnChange = this.handleColumnChange.bind(this);
        this.rowGetter = this.rowGetter.bind(this);
    }

    componentDidMount() {
        api.input(this.props.wfModuleId)
            .then(input_data => {
                var nxt_state = Object.assign({}, this.state);
                nxt_state.columns = input_data.columns.map((cname, i) => ({key: 'col' + i.toString(), name: cname}));
                nxt_state.columns_loaded = true;
                this.setState(nxt_state);
            })
    }

    handleColumnChange(event) {
        console.log(event.target.value);
        var target_col = event.target.value;
        api.histogram(this.props.wfModuleId, target_col)
            .then(histogram => {
                var nxt_state = Object.assign({}, this.state);
                nxt_state.histogram = histogram;
                nxt_state.histogram_loaded = true;
                nxt_state.histogram_columns = histogram.columns.map(cname => ({key: cname, name: cname, editable: !(cname == 'count')}));
                nxt_state.current_column = target_col;
                this.setState(nxt_state);
            });
        //this.saveStateToDatabase(this.state);
        this.props.paramChanged({selected_column: this.state.current_column});
    }

    rowGetter(i) {
        return this.state.histogram.rows[i];
    };

    renderColumnSelect() {
        const options = this.state.columns.map(col => (<option key={col.key}>{col.name}</option>));
        if(this.state.columns_loaded) {
            return (
                <FormGroup>
                    <Label for="exampleSelect">Select a column</Label>
                    <Input type="select" name="select" id="exampleSelect" value={this.state.current_column} onChange={this.handleColumnChange}>
                        <option key='colplaceholder' disabled>Select a column</option>
                        {options}
                  </Input>
                </FormGroup>
            );
        }
        return (<div>Loading data...</div>);
    }

    renderHistogram() {
        if(this.state.histogram_loaded) {
            return (
                <ReactDataGrid
                    enableCellSelect={true}
                    columns={this.state.histogram_columns}
                    rowGetter={this.rowGetter}
                    rowsCount={this.state.histogram.total_rows}
                    minHeight={350}
                    rowHeight={35}
                />
            )
        }
        return (<div></div>);
    }

    //saveStateToDatabase(state) {
    //    var current_column = state.current_column;
    //    store.dispatch(changeParamAction(this.props.wfModuleId, 'selected_column', current_column));
    //}

    render() {
        const column_select = this.renderColumnSelect();
        const histogram_datagrid = this.renderHistogram();
        return (
            <div>
                {column_select}
                <br />
                {histogram_datagrid}
                <br />
            </div>
        )
    }
};