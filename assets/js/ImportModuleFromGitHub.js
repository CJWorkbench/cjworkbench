import React from 'react'
import { Button, UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import PropTypes from 'prop-types'

import { csrfToken } from './utils'


export default class ImportModuleFromGitHub extends React.Component {
  constructor(props) {
    super(props);
    this.state = {url: ''};

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.cancel = this.cancel.bind(this);
    this.onKeyPress = this.keyPress.bind(this);

    this.moduleLibrary = this.props.moduleLibrary;
  }

  keyPress(event) {
    event.preventDefault(); // stops the page from refreshing... someday I'll understand why. 
    if (e.key == 'Enter') {
      handleSubmit(event);
    }
  }

  cancel(event) {
    this.moduleLibrary.setImportFromGitHubComponentVisibility(false);
  }

  handleChange(event) {
    this.setState({url: event.target.value});
  }

  handleSubmit(event) {
      event.preventDefault(); // stops the page from refreshing... someday I'll understand why. 
      var url = '/api/importfromgithub/';
      var eventData = {'url': this.state.url};
      fetch(url, {
        method: 'post',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(eventData)
      });
  }

  render() {
    return (
      <form onSubmit={this.handleSubmit}>
        <div className="import-module-label">
          Import module from GitHub:
          <input type="text" 
                 className="data-paragraph-g text-field mt-2"
                 value={this.state.value} 
                 onChange={this.handleChange} 
                 onKeyPress={this.handleChange}
                 />
        </div>
        <div className="import-module-buttons">
          <Button onClick={this.cancel.bind(this)} 
            className='button-blue'>Cancel</Button>
          <Button onClick={this.handleSubmit.bind(this)} style={{'margin-left': '20px'}}
            className='button-blue'>Submit</Button>
        </div>
      </form>
    );
  }
}


ImportModuleFromGitHub.propTypes = {
  url:  PropTypes.string,
};
