// Choose some columns

import React from 'react';
import ReactDataGrid from 'react-data-grid';
import PropTypes from 'prop-types'

export default class ColumnRenamer extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
        columns: [
            {
                key: 'oldName',
                name: 'Old',
                width: 115
            },
            {
                key: 'newName',
                name: 'New',
                editable: true
            }
        ],
        oldColNames: [],
        newColNames: []
    };
    this.rowGetter = this.rowGetter.bind(this);
    this.handleGridRowsUpdated = this.handleGridRowsUpdated.bind(this);
  }

  // column renaming parameter string + current column names -> array of new column names
  parseNewColNames(nameParam, cols) {
    var newColNames = cols.slice();

    // We may have different columns than when we started. Keep whichever are still there.
    if (nameParam && nameParam.length > 0) {

      // Reset all column names if we can't parse data for any reason
      try {
        var nameMap = JSON.parse(nameParam);
      } catch (e) {
        return newColNames;
      }

      for (var i = 0; i < cols.length; i++) {
        let c = cols[i];
        if (nameMap.hasOwnProperty(c)) {
          newColNames[i] = nameMap[c];
        }
      }
    }

    return newColNames
  }

  loadColNames() {
    this.props.getColNames()
      .then(cols => {
        this.setState({
          oldColNames: cols,
          newColNames: this.parseNewColNames(this.props.renameParam, cols)});
      });
  }

  // Load column names when first rendered
  componentDidMount() {
    this.loadColNames();
  }

  // Update column names when workflow revision bumps
  componentWillReceiveProps(nextProps) {
    if (this.props.revision != nextProps.revision) {
      this.loadColNames();
    }
  }

  handleGridRowsUpdated({ fromRow, toRow, updated }) {
    if (!this.props.isReadOnly) {
      let newColNames = this.state.newColNames.slice();

      for (let i = fromRow; i <= toRow; i++) {
        newColNames[i] = updated['newName'];
      }

      this.setState({ newColNames: newColNames });

      var nameMap = {};
      let cols = this.state.oldColNames;
      for (let i=0; i<cols.length; i++) {
        nameMap[cols[i]] = newColNames[i];
      }

      this.props.saveState(JSON.stringify(nameMap));
    }
  }

  rowGetter(i) {
    return {'oldName': this.state.oldColNames[i], 'newName': this.state.newColNames[i]};
  }


  render() {
    return  (
      <div className='table-module-wrapper'>
        <ReactDataGrid
          enableCellSelect={!this.props.isReadOnly}
          columns={this.state.columns}
          rowGetter={this.rowGetter}
          rowsCount={this.state.oldColNames.length}
          minHeight={200}
          onGridRowsUpdated={this.handleGridRowsUpdated} />
      </div>
        );
  }
}

ColumnRenamer.propTypes = {
  renameParam:  PropTypes.string.isRequired,
  saveState:    PropTypes.func.isRequired,
  getColNames:  PropTypes.func.isRequired,
  revision:     PropTypes.number.isRequired
};
