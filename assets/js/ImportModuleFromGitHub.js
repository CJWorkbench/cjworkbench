import React from 'react'
import { Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
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
    this.state = {
      modalOpen: false,
      url: '',
      message_type: '',
      message: null
    };
    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.onKeyPress = this.keyPress.bind(this); // to handle user hitting enter, which then submits
    this.moduleLibrary = this.props.moduleLibrary;
    this.handleResponse = this.handleResponse.bind(this);
    this.toggleModal = this.toggleModal.bind(this);
  }

  keyPress(event) {
    event.preventDefault(); // stops the page from refreshing
    if (e.key == 'Enter') {
      handleSubmit(event);
    }
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
      event.preventDefault(); // stops the page from refreshing
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

  // opens/closes modal, and resets message state
  toggleModal() {
    this.setState({
      modalOpen: !this.state.modalOpen ,
      message_type: '',
      message: null
    });
  }

  render() {

    var visible = null;

    if (this.state.message) {
      if (this.state.message_type == 'error') {
        visible =
          <div>
            <div className="import-github-error">
              Error importing module from GitHub: {this.state.message}
            </div>
            <div className="import-github-response-button">
              <div onClick={this.toggleModal} className='button-blue action-button'>
                OK
              </div>
            </div>
          </div>
      } else if (this.state.message_type == 'success') {
        var json = JSON.parse(this.state.message);
        visible =
          <div>
            <div className="import-github-success">
              Successfully imported {json.author}'s module "{json.name}" under category "{json.category}".
            </div>
            <div className="import-github-response-button">
              <div onClick={this.toggleModal} className='button-blue action-button'>
                OK
              </div>
            </div>
          </div>
      }
    } else {
      visible =
        <div className="import-module-buttons d-flex flex-row">
          <div onClick={this.toggleModal} className='button-gray action-button'>
            Cancel
          </div>
          <div onClick={this.handleSubmit.bind(this)} className='button-blue action-button ml-3'>
            Submit
          </div>
        </div>
    };


    return (
      <div>

        <div className='import-module-button content-3 mb-5' onClick={ this.toggleModal }>
          IMPORT FROM GITHUB
        </div>;

        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className='dialog-window'>
          <ModalHeader toggle={this.toggleModal} >
            <div className='title-4 t-d-gray'>Import from GitHub</div>
          </ModalHeader>
          <ModalBody className='dialog-body'>
            <form onSubmit={this.handleSubmit}>
              <div className="label-margin t-d-gray content-3">Git Url:</div>
              <div className="import-url-field">
                <input type="text"
                      className="text-field mt-2 t-m-gray content-3"
                      value={this.state.value}
                      placeholder='https://github.com..'
                      onChange={this.handleChange}
                      onKeyPress={this.handleChange}
                      />
              </div>
              {visible}
            </form>
          </ModalBody>
        </Modal>

      </div>
    );
  }
}


ImportModuleFromGitHub.propTypes = {
  moduleLibrary: PropTypes.object.isRequired
};
