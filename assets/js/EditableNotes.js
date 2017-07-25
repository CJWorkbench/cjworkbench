import React from 'react';
import _ from 'lodash';
import { RIETextArea } from 'riek';
import workbenchapi from './WorkbenchAPI';
import PropTypes from 'prop-types'

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
    console.log("Changing note on wf module " + this.props.wfModuleId + " to: " + newNote.value)
    this.api.setWfModuleNotes(this.props.wfModuleId, newNote.value);
  }

  // can specify rows and cols in parameters
  render() {
    return <div><RIETextArea
      value={this.props.value}
      change={this.saveNotes}
      propName="value"
      className={this.props.editClass}
      cols={150}
      rows={10}
    /></div>
  }
}

EditableNotes.propTypes = {
  value:          PropTypes.string,
  wfModuleId:     PropTypes.number
};
