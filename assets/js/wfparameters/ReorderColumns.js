import React from 'react'
import PropTypes from 'prop-types'
import {idxToLetter} from "../utils";
import {Table} from 'reactstrap';

export default class ReorderHistory extends React.Component {
    render() {
        let historyStr = this.props.history.trim();
        let history = (historyStr.length > 0) ? JSON.parse(historyStr) : [];
        let historyRows = history.map((entry, idx) => {
            return (
                <tr key={idx}>
                    <td>{idx + 1}</td>
                    <td>{entry.column}</td>
                    <td>{idxToLetter(entry.from)}</td>
                    <td>{idxToLetter(entry.to)}</td>
                </tr>
            );
        });

        return (
            <Table>
                <thead>
                    <tr>
                        <td>#</td>
                        <td>Column</td>
                        <td>From</td>
                        <td>To</td>
                    </tr>
                </thead>
                <tbody>
                    {historyRows}
                </tbody>
            </Table>
        );
    }
}
