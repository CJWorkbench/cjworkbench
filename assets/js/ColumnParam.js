// Pick a single column
import React from 'react'
import PropTypes from 'prop-types'


export default class ColumnParam extends React.Component {
  constructor(props) {
    super(props);
    this.state = { colNames: [], selectedCol: props.selectedCol };
    this.onChange = this.onChange.bind(this);
  }

  loadColNames() {
    this.props.getColNames()
      .then(cols => {

        // Always make it possible to select (or show) "(None)"
        var colsPlusNone = ['(None)'].concat(cols);
        this.setState({colNames: colsPlusNone});
      });
  }

  // Load column names when first rendered
  componentDidMount() {
    this.loadColNames();
  }

  // Update our checkboxes when we get new props = new selected column
  // And also column names when workflow revision bumps
  componentWillReceiveProps(nextProps) {
    this.setState({selectedCol: nextProps.selectedCol});
    if (this.props.revision != nextProps.revision) {
      this.loadColNames();
    }
  }

  onChange(evt) {
    var colName = this.state.colNames[evt.target.value];
    if (colName == "(None)") {
      colName = ""; // user should see "please select column" not "no column named (None)"
    }
    this.setState({selectedCol: colName});
    this.props.onChange(colName);
  }

  render() {

    // Select the current column name if any, otherwise (None)
    var idx = this.state.colNames.indexOf(this.state.selectedCol);
    if (idx == -1) {
      idx = 0;
    }

    var itemDivs = this.state.colNames.map( (name, idx) => {
        return <option key={idx} value={idx} className='dropdown-menu-item t-d-gray content-3'>{name}</option>;
    });

    return (
        <select
          className='custom-select dropdown-selector'
          value={idx}
          onChange={this.onChange}
          disabled={this.props.isReadOnly}
        >
          {itemDivs}
        </select>
    );
  }
}

ColumnParam.propTypes = {
  selectedCol:    PropTypes.string.isRequired,
  getColNames:    PropTypes.func.isRequired,
  isReadOnly:     PropTypes.bool.isRequired,
  revision:       PropTypes.number.isRequired,
  onChange:       PropTypes.func.isRequired
};
