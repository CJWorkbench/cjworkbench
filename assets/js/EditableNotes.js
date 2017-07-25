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
    this.api.setWfModuleNotes(this.props.wfModuleId, newNote.value);
  }

  // can specify rows and cols in parameters
  render() {
    // var rowCount = (this.props.value && this.props.value.length > 50)
    //   ? 5
    //   : 1

    var value = (this.props.value) ? this.props.value : "   "

    return <div><RIETextArea
      value={value}
      change={this.saveNotes}
      propName="value"
      className={this.props.editClass}
      cols={50}
      rows={5}
    /></div>
  }
}

EditableNotes.propTypes = {
  value:          PropTypes.string,
  wfModuleId:     PropTypes.number
};
