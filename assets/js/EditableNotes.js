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
    this.keyPress = this.keyPress.bind(this);
    this.state = {
      value: this.props.value
    }
  }

  // Simulate a click on the field to enter editing state upon mount
  //    Have to target child through parent b/c RIETextArea cannot be directly referenced
  componentDidMount() {
    if (this.props.startFocused) 
      this.textInput.childNodes[0].focus();
  }

  // Make Enter key save the text in edit field, overriding default newline
  keyPress(e) {
    if (e.key == 'Enter' ) {
      e.preventDefault();
      this.saveNotes({value: e.target.value});
    }
  }

  // If nothing entered, saves a default note and closes
  saveNotes(newNote) {
    if (!newNote.value || (newNote.value == "")) {
      this.api.setWfModuleNotes(this.props.wfModuleId, "Write notes here");
      this.props.hideNotes();
    } else {
      this.api.setWfModuleNotes(this.props.wfModuleId, newNote.value);
    }
  }


  render() {

    var rowCount = (this.props.value && this.props.value.length)
      ? Math.ceil(this.props.value.length / 80)
      : 1

    // 'ref' callback receives the mounted instance of the component as its argument
    // classEditing param for classes applied during edit state only
    return <div
              onKeyPress={this.keyPress}
              ref={ (input) => { this.textInput = input; } }
              className='m-6'
            >
            {this.props.isReadOnly ? (
              <textarea readOnly="true" value={this.props.value}></textarea>
            ):(
              <RIETextArea
                value={this.props.value}
                change={this.saveNotes}
                propName="value"
                className={this.props.editClass}
                classEditing='editable-notes-field-active'
                rows={rowCount}
              />
            )}
          </div>
  }
}

EditableNotes.propTypes = {
  value:          PropTypes.string,
  wfModuleId:     PropTypes.number,
  hideNotes:      PropTypes.func
};
