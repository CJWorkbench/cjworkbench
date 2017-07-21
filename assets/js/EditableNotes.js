import React from 'react';
import _ from 'lodash';
import { RIETextArea } from 'riek';
import workbenchapi from './WorkbenchAPI';

export default class EditableNotes extends React.Component {
  constructor(props) {
    super(props);
    this.api = workbenchapi();
    this.saveNotes = this.saveNotes.bind(this);
    this.state = {
      value: this.props.value
    }
  }

  saveNotes(newNote) {
    console.log("New Note entered, attempting to save.")
    this.api.setWfModuleNotes(this.props.wf_module_id, newNote.value);
  }

  // can specify rows and cols in parameters
  render() {
    return <div><RIETextArea
      value={this.props.value}
      change={this.saveNotes}
      propName="value"
      className={this.props.editClass}
    /></div>
  }
}
