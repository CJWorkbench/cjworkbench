// Choose some columns
import React from 'react'
import PropTypes from 'prop-types'


export default class ColumnSelector extends React.Component {
  constructor(props) {
    super(props);
    this.state = { colNames: [], selected: this.parseSelectedCols(props.selectedCols) };
    this.clicked = this.clicked.bind(this);
    this.selectAllClicked = this.selectAllClicked.bind(this);
    this.selectNoneClicked = this.selectNoneClicked.bind(this);
  }

  // selected columns string -> array of column names
  parseSelectedCols(sc) {
    var selectedColNames = (typeof sc !== 'undefined') ? sc.trim() : '';
    return selectedColNames.length > 0 ? selectedColNames.split(',') : [];   // empty string should give empty array
  }

  loadColNames() {
    this.props.getColNames()
      .then(cols => {
        // Remove selected columns that no longer exist
        var newSel = this.state.selected.filter( n => cols.includes(n) );
        this.setState({colNames: cols, selected: newSel});
      });
  }

  // Load column names when first rendered
  componentDidMount() {
    this.loadColNames();
  }

  // Update our checkboxes when we get new props = new selected columns string
  // And also column names when workflow revision bumps
  componentWillReceiveProps(nextProps) {
    this.setState({colNames: this.state.colNames, selected: this.parseSelectedCols(nextProps.selectedCols)});
    if (this.props.revision != nextProps.revision) {
      this.loadColNames();
    }
  }

  clicked(e) {
    var checked = e.target.checked;
    var colName = e.target.attributes.getNamedItem('data-name').value;
    var newSelected = undefined;

    if (checked && !(this.state.selected.includes(colName))) {
      // Not there, add it
      newSelected = this.state.selected.slice();
      newSelected.push(colName);
    } else if (!checked && (this.state.selected.includes(colName))) {
      // Is there, remove it
      newSelected = this.state.selected.filter( n => n!=colName )
    }

    if (newSelected) {
      this.setState({colNames: this.state.colNames, selected: newSelected});
      this.props.saveState(newSelected.join())
    }
  }

  selectAllClicked() {
      var newSelected = this.state.colNames.slice();
      this.setState({colNames: this.state.colNames, selected: newSelected});
      this.props.saveState(newSelected.join());
  }

  selectNoneClicked() {
      var newSelected = [];
      this.setState({colNames: this.state.colNames, selected: newSelected});
      this.props.saveState(newSelected.join());
  }

  render() {
    // use nowrap style to ensure checkbox label is always on same line as checkbox
    const checkboxes = this.state.colNames.map( n => {
      return (
          <div className='checkbox-container' style={{'whiteSpace': 'nowrap'}} key={n}>
              <input
                  type='checkbox'
                  disabled={this.props.isReadOnly}
                  checked={this.state.selected.includes(n)}
                  onChange={this.clicked}
                  data-name={n}
              ></input>
              <span className='t-d-gray checkbox-content content-3'>{n}</span>
          </div>
        );
      });

    return (
      // The name attributes in the buttons are used for selection in tests. Do not change them.
      <div className='container list-wrapper'>
          <button
              disabled={this.props.isReadOnly}
              onClick={this.selectAllClicked}
              name={'mc-select-all'} >
              Select all
          </button>
          <button
              disabled={this.props.isReadOnly}
              onClick={this.selectNoneClicked}
              name={'mc-select-none'} >
              Select none
          </button>
          <div className='row list-scroll'>
              { checkboxes }
          </div>
      </div>
    );
  }
}

ColumnSelector.propTypes = {
  selectedCols: PropTypes.string.isRequired,
  saveState:    PropTypes.func.isRequired,
  getColNames:  PropTypes.func.isRequired,
  isReadOnly:   PropTypes.bool.isRequired,
  revision:     PropTypes.number.isRequired
};
