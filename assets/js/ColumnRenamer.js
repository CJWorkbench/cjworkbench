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
                name: 'Current',
                width: 200
            },
            {
                key: 'newName',
                name: 'New',
                editable: true
            }
        ],
        oldColNames: [],
        newColNames: this.parseNewColNames(props.newNameCols)
    }
    this.rowGetter = this.rowGetter.bind(this);
    this.handleGridRowsUpdated = this.handleGridRowsUpdated.bind(this);
  }

    // selected columns string -> array of column names
  parseNewColNames(sc) {
    var newColNames =  sc != undefined ? sc.trim() : '';
    return newColNames.length>0 ? newColNames.split(',') : [];   // empty string should give empty array
  }

  loadColNames() {
     console.log(this.state.newColNames)
     if (this.state.newColNames.length == 0){
         console.log('empty');
        this.props.getColNames()
          .then(cols => {
            this.setState({oldColNames: cols, newColNames: cols});
          })
      }
     else {
         console.log('full');
         this.props.getColNames()
             .then(cols => {
                 this.setState({oldColNames: cols, newColNames: this.parseNewColNames(this.props.newNameCols)});
             });
     }
  }
      // Load column names when first rendered
  componentDidMount() {
    this.loadColNames();
  }

  // Update column names when workflow revision bumps
  componentWillReceiveProps(nextProps) {
      console.log('componentWillReceiveProps '+ nextProps.newNameCols);
    if (this.props.revision != nextProps.revision) {
        this.setState({oldColNames: this.state.oldColNames, newColNames: this.parseNewColNames(nextProps.newNameCols)});
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
      this.props.saveState(newColNames.join());
      console.log(newColNames);
    }
  }

  rowGetter(i) {
    return {'oldName': this.state.oldColNames[i], 'newName': this.state.newColNames[i]};
  }


  render() {
    return  (
      <ReactDataGrid
        enableCellSelect={!this.props.isReadOnly}
        columns={this.state.columns}
        rowGetter={this.rowGetter}
        rowsCount={this.state.oldColNames.length}
        minHeight={200}
        onGridRowsUpdated={this.handleGridRowsUpdated} />);
  }
}

ColumnRenamer.propTypes = {
  saveState:    PropTypes.func,
  getColNames:  PropTypes.func,
  revision:     PropTypes.number
};
