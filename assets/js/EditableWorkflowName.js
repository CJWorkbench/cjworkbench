import React from 'react';
import EditableText from './EditableText';
import workbenchapi from './WorkbenchAPI';

export default class EditableWorkflowName extends EditableText {
  constructor(props) {
    super(props);
    this.api = workbenchapi();
  }

  saveChanges(newName) {
    this.api.setWfName(this.props.wfId, this.state.value).then((result) => {
      console.log(result);
    });
  }

  render() {
    if (this.state.editing == true) {
      return <input
        className={this.props.editClass}
        onBlur={this.onBlur}
        type="text"
        ref={(input) => { this.editInput = input }}
        value={this.state.value}
        onChange={this.onChange}
      />
    }
    return <h4 onClick={this.toggleEditing}>{this.state.value}</h4>;
  }
}
