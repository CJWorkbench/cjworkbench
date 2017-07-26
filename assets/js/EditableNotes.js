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
    // save something in text field in case of no value existing
    var value = (newNote.value) ? newNote.value : "   "

    this.api.setWfModuleNotes(this.props.wfModuleId, value);
  }

  render() {
    var rowCount = (this.props.value && this.props.value.length > 70)
      ? 5
      : 1

    // show something in text field in case of no value existing
    var value = (this.props.value) ? this.props.value : "   "

    return <div><RIETextArea
      value={value}
      change={this.saveNotes}
      propName="value"
      className={this.props.editClass}
      cols={70}
      rows={rowCount}
    /></div>
  }
}

EditableNotes.propTypes = {
  value:          PropTypes.string,
  wfModuleId:     PropTypes.number
};
