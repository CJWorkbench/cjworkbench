import React from 'react'
import { Button } from 'reactstrap'
import PropTypes from 'prop-types'

import { csrfToken } from './utils'

/**
 * Component that handles the Import from GitHub functionality. This functionality allows users
 * to insert a URL to a GitHub repository in a textfield, and, if there are no errors, 
 * a new module is added to the Module Library. 
 * 
 * Currently, users can't set any entitlements on these modules. Also, there is no client-side 
 * validation albeit maybe there should be? 
 */

export default class ImportModuleFromGitHub extends React.Component {
  constructor(props) {
    super(props);
    this.state = {url: ''};

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.cancel = this.cancel.bind(this); 
    this.onKeyPress = this.keyPress.bind(this); // to handle user hitting enter, which then submits

    this.moduleLibrary = this.props.moduleLibrary;

    this.handleResponse = this.handleResponse.bind(this);
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

  /**
   * Keep the state updated with the latest value of the textfield. 
   * 
   * @param {*} event: any changes to the textfield. 
   */
  handleChange(event) {
    this.setState({url: event.target.value});
  }

  /**
   * When the user hits Submit or the 'Enter' key, then this function is invoked, passing down
   * the user-entered URL to the server, which validates the URL and, if valid, imports the 
   * module. 
   * 
   * @param {*} event 
   */
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
      })
      .then((result) => result.json())
      .then((result) => {
        this.handleResponse(result);
      })
      .then(() => {
        this.moduleLibrary.updated(true);
      })
  }

  handleResponse(response) {
    // handle error callback
    if (response.error) {
      this.setState({
        message_type: "error", 
        message: response.error
      });
    } else { // handle success callback
      this.setState({
        message_type: "success", 
        message: response // contains the JSON with all the fields we might want to display. 
      })
    }
  }

  render() {

    // what is visible? 
    var visible = null; 

    var cancelButton = <Button onClick={this.cancel.bind(this)} 
            className='button-blue'>Cancel</Button>

    if (this.state.message) {
      var json = JSON.parse(this.state.message)
      if (this.state.message_type == 'error') {
        visible = <div><div className="import-github-error">
            Error importing module from GitHub: 
            {json}
          </div>
          <div className="import-github-response-button">
            <Button onClick={this.cancel.bind(this)} 
                className='button-blue'>OK</Button>
          </div></div>
      } else if (this.state.message_type == 'success') {
        visible = <div><div className="import-github-success">
          Successfully imported {json.author}'s module "{json.name}" under category "{json.category}".
        </div>
        <div className="import-github-response-button">
            <Button onClick={this.cancel.bind(this)} 
                className='button-blue'>OK</Button>
          </div></div> 
      }
    } else {
      visible = <div className="import-module-buttons">
          <Button onClick={this.cancel.bind(this)} 
            className='button-blue'>Cancel</Button>
          <Button onClick={this.handleSubmit.bind(this)} 
            style={{'marginLeft': '20px'}} // spacing between buttons.
            className='button-blue'>Submit</Button>
        </div>
    }

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
        {visible}
      </form>
    );
  }
}


ImportModuleFromGitHub.propTypes = {
  url:  PropTypes.string,
};
