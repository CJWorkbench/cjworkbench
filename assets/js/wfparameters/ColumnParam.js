// Pick a single column
import React from 'react'
import PropTypes from 'prop-types'


export default class ColumnParam extends React.Component {
  constructor(props) {
    super(props);
    this.selectRef = null;
    this.state = { colNames: [], selectedCol: props.selectedCol };
    this.onChange = this.onChange.bind(this);
  }

  loadColNames() {
    this.props.getColNames()
      .then(cols => {

        // Always make it possible to select (or show) "(None)"
        let select_string = this.props.noSelectionText || 'Select';
        var colsPlusNone = [select_string].concat(cols);
        this.setState({colNames: colsPlusNone});
      });
  }

  // Load column names when first rendered
  componentDidMount() {
    this.loadColNames();
  }

  // Update when we get new props = new selected column
  // And also column names when workflow revision bumps
  componentWillReceiveProps(nextProps) {
    this.setState({selectedCol: nextProps.selectedCol});
    if (this.props.revision !== nextProps.revision) {
      this.loadColNames();
    }
  }

  onChange(evt) {
    let colName;
    if (this.selectRef.selectedIndex === 0) {
      colName = "";  // no selection
    } else {
      colName = this.state.colNames[evt.target.value];
    }

    this.setState({selectedCol: colName});
    this.props.onChange(colName);
  }

  render() {

    // Select the current column name if any, otherwise (None)
    var idx = this.state.colNames.indexOf(this.state.selectedCol);
    if (idx === -1) {
      idx = 0;
    }

    var itemDivs = this.state.colNames.map( (name, idx) => {
        return <option key={idx} value={idx} className='dropdown-menu-item t-d-gray content-3'>{name}</option>;
    });

    return (
        <select
          className='custom-select parameter-base dropdown-selector'
          value={idx}
          onChange={this.onChange}
          disabled={this.props.isReadOnly}
          ref={(ref) => this.selectRef= ref}
        >
          {itemDivs}
        </select>
    );
  }
}

ColumnParam.propTypes = {
  selectedCol:    PropTypes.string.isRequired,
  getColNames:    PropTypes.func.isRequired,
  noSelectionText:PropTypes.string,
  isReadOnly:     PropTypes.bool.isRequired,
  revision:       PropTypes.number.isRequired,
  onChange:       PropTypes.func.isRequired
};
