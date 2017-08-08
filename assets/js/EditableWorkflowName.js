import React from 'react';
import _ from 'lodash';
import { RIETextArea } from 'riek';
import PropTypes from 'prop-types'

export default class EditableWorkflowName extends React.Component {
  constructor(props) {
    super(props);
    this.saveName = this.saveName.bind(this);
    this.keyPress = this.keyPress.bind(this);    
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
    this.props.api.setWfName(this.props.wfId, value);
  }

  // Make Enter key save the text in edit field, overriding default newline
  keyPress(e) {
    if (e.key == 'Enter' ) {
      e.preventDefault();
      this.saveName({value: e.target.value});
    }
  }

  // classEditing param for classes applied during edit state only
  render() {

    // This does not play well with smaller screens
    var rowCount = (this.state.value && this.state.value.length)
      ? Math.ceil(this.state.value.length / 30)
      : 1

    return <div onKeyPress={this.keyPress}>
      {this.props.isReadOnly ? (
        <span className={this.props.editClass}>{this.state.value}</span>
      ):(
        <RIETextArea
          value={this.state.value}
          change={this.saveName}
          propName="value"
          className={this.props.editClass}
          classEditing='editable-title-field-active'
          rows={rowCount}
        />
      )}
    </div>
  }
}

EditableWorkflowName.propTypes = {
  value:    PropTypes.string,
  wfId:     PropTypes.number,
  api:      PropTypes.object.isRequired,
};
