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
    console.log("Changing wf name to " + newName.value)
    this.api.setWfName(this.props.wfId, newName.value);
  }

  render() {
    return <h4><RIEInput
      value={this.props.value}
      change={this.saveName}
      propName="value"
      className={this.props.editClass}
    /></h4>
  }
}

EditableWorkflowName.propTypes = {
  value:    PropTypes.string,
  wfId:     PropTypes.number
};


