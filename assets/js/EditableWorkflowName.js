import React from 'react';
import Textarea from 'react-textarea-autosize';
import PropTypes from 'prop-types'

export default class EditableWorkflowName extends React.Component {
  constructor(props) {
    super(props);
    this.saveName = this.saveName.bind(this);
    this.handleChange = this.handleChange.bind(this);
    this.handleClick = this.handleClick.bind(this);
    this.keyPress = this.keyPress.bind(this);
    this.state = {
      value: this.props.value
    }
  }

  handleChange(event) {
    this.setState({value: event.target.value});
  }

  // selects the text for editing on a click
  handleClick(event) {
    if (!this.props.isReadOnly) this.textInput.childNodes[0].select();
  }

  // Make Enter key save the text in edit field, overriding default newline
  keyPress(e) {
    if (e.key == 'Enter' ) {
      e.preventDefault();
      // Blur event will trigger save
      // Have to target child through parent b/c TextArea cannot be directly referenced
      this.textInput.childNodes[0].blur();
    }
  }

  saveName() {
    this.props.api.setWfName(this.props.workflowId, this.state.value);
  }

  render() {

    return <div
              // Saves a reference to parent to allow targeting of imported component
              ref={(input) => {this.textInput = input;}}
              onClick={this.handleClick}
              className='editable-title--container'
            >
              {this.props.isReadOnly
                ? ( <span className='editable-title--field'>{this.props.value}</span> )
                : (
                    <input type="text"
                      value={this.state.value}
                      onChange={this.handleChange}
                      onBlur={this.saveName}
                      onKeyPress={this.keyPress}
                      className='editable-title--field'
                    />
                  )
              }
          </div>
  }
}


EditableWorkflowName.propTypes = {
  value:      PropTypes.string,
  workflowId:       PropTypes.number,
  api:        PropTypes.object.isRequired,
  isReadOnly: PropTypes.bool
};
