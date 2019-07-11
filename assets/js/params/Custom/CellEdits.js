import React from 'react'
import PropTypes from 'prop-types'

export default class CellEdits extends React.Component {
  static propTypes = {
    value: PropTypes.arrayOf(PropTypes.shape({
      row: PropTypes.number.isRequired,
      col: PropTypes.string.isRequired,
      value: PropTypes.string.isRequired
    }).isRequired).isRequired
  }

  // Starting from a JSON array like this
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
  get editList () {
    const { value } = this.props
    const edits = {}

    for (const edit of value) {
      const colName = edit.col
      const colEdits = edits[colName] || []
      colEdits.push({ row: edit['row'], value: edit['value'] })
      edits[colName] = colEdits
    }

    // Sort column names and convert to array
    const colNames = Object.keys(edits)
    colNames.sort()

    const editsArray = colNames.map(colName => ({
      col: colName,
      edits: edits[colName].sort((a, b) => a.row - b.row)
    }))

    return editsArray
  }

  render () {
    return (
      <React.Fragment>
        {this.editList.map(({ col, edits }) => (
          <div className='cell-edits--column' key={col}>
            <div className='edited-column'>{col}</div>
            <div className='cell-edits--rows'>
              {edits.map(({ row, value }, idx) => (
                <div className='cell-edits--row' key={idx}>
                  <div className='edited-row'>{row + 1}</div>
                  <div className='edited-text'>{value}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </React.Fragment>
    )
  }
}
