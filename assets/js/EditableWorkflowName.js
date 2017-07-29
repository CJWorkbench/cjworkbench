import React from 'react';
import _ from 'lodash';
import { RIEInput } from 'riek';
import workbenchapi from './WorkbenchAPI';
import PropTypes from 'prop-types'

export default class EditableWorkflowName extends React.Component {
  constructor(props) {
    super(props);
    this.api = workbenchapi();
    this.saveName = this.saveName.bind(this);
    this.state = {
      value: this.props.value
    }
  }

  saveName(newName) {
    // If blank entry, use default title
    var value = newName.value;
    if (!value || (value == "")) {
      value = "Untitled Workflow";
    }
    this.setState({value: value});
    this.api.setWfName(this.props.wfId, value);
  }

  // classEditing param for classes applied during edit state only
  render() {
    return <h4><RIEInput
      value={this.state.value}
      change={this.saveName}
      propName="value"
      className={this.props.editClass}
      classEditing='title-1 t-d-gray'
    /></h4>
  }
}

EditableWorkflowName.propTypes = {
  value:    PropTypes.string,
  wfId:     PropTypes.number
};


