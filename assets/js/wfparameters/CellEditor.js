// Displays edits made to individual cells

import React from 'react';
import PropTypes from 'prop-types'

export default class CellEditor extends React.Component {
  // Starting from a JSON string that represents an array like this
  // [
  //   { row: 3, col: 'foo', value:'bar' },
  //   { row: 6, col: 'food', value:'sandwich' },
  //   ...
  // ]
  // convert it to one that combines all edits for single column, like this
  // [
  //   { col: 'foo', edits: [ { row: 3, value: 'bar'}, ... ] },
  //   { col: 'food', edits: [ { row: 6, value: 'sandwich}, ... ] },
  // ]

  parseEditList(edit_json) {

    let unsorted_edits;
    try {
      unsorted_edits = JSON.parse(edit_json);
    } catch(err) {
      return [];    // error parsing JSON, most likely because of empty parameter
    }

    let edits = {};

    for (let edit of unsorted_edits) {
      let colName = edit.col;
      let colEdits = edits[colName] || [];
      colEdits.push({ row: edit['row'], value: edit['value']});
      edits[colName] = colEdits;
    }

    // Sort column names and convert to array
    let colNames = Object.keys(edits);
    colNames.sort();

    let editsArray = colNames.map( (colName) => {
      return { col: colName, edits: edits[colName] };
    });

    return editsArray;
  }


  render() {

    let edits = this.parseEditList(this.props.edits);

    // Each column gets a div
    var editList = edits.map((colEdits) => {

      // Each row in this list of edits for this column also gets div love
      let rows = colEdits['edits'].map( (row, idx) => {
        return (
          <div className='cell-edits--row' key={idx}>
            <div className='edited-row'>{row['row']+1}</div>
            <div className='edited-text'>{row['value']}</div>
          </div>
        );
      });

      let colName = colEdits['col'];
      return (
        <div className='cell-edits--column' key={colName}>
          <div className='edited-column'>{ colName }</div>
          <div className='cell-edits--rows'>
            { rows }
          </div>
        </div>
      );
    });

    return  (
      <div>
        { editList }
      </div>
    );
  }
}

CellEditor.propTypes = {
  edits:        PropTypes.string.isRequired,
  onSave:       PropTypes.func.isRequired,
};
