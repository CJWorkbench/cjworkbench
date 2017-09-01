import React from 'react';
import Textarea from 'react-textarea-autosize';
import PropTypes from 'prop-types'

export default class EditableWorkflowName extends React.Component {
  constructor(props) {
    super(props);
    this.saveName = this.saveName.bind(this);
    this.handleChange = this.handleChange.bind(this);
    this.keyPress = this.keyPress.bind(this);
    this.state = {
      value: this.props.value
    }
  }

  handleChange(event) {
    this.setState({value: event.target.value});
  }

  // Make Enter key save the text in edit field, overriding default newline
  keyPress(e) {
    if (e.key == 'Enter' ) {
      e.preventDefault();
      // blur event will trigger save 
      // Have to target child through parent b/c TextArea cannot be directly referenced
      this.textInput.childNodes[0].blur();
    }
  }

  saveName() {
    this.props.api.setWfName(this.props.wfId, this.state.value);
  }
  
  render() {

    // Saves a ref to parent to allow targeting of imported component
    return <div ref={(input) => {this.textInput = input;}}>
            {this.props.isReadOnly 
              ? ( <span className='content-3 t-d-gray'>{this.props.value}</span> )
              : ( 
                  <Textarea
                    value={this.state.value}
                    onChange={this.handleChange}
                    onBlur={this.saveName}
                    onKeyPress={this.keyPress}
                    className='editable-title-field'
                    maxRows={1}
                  />
                )
            }
          </div>
  }
}


EditableWorkflowName.propTypes = {
  value:      PropTypes.string,
  wfId:       PropTypes.number,
  api:        PropTypes.object.isRequired,
  isReadOnly: PropTypes.bool
};

