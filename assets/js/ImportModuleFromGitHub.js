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
      .then(result => result.json())
      .then(json => this.handleResponse(json),
            error => this.handleResponse(null)) // 500 error
      .then(() => {
        this.props.moduleAdded();
      })
  }

  handleResponse(response) {
    if (response === null) {
      this.setState({
        message_type: "error",
        message: "Server error"
      });
    } else if (response.error) {
      this.setState({
        message_type: "error",
        message: response.error
      });
    } else {
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
                <div>{this.state.message}</div>
            </div>
            <div className="d-flex flex-row modal-dual-button">
                <div onClick={this.toggleModal} className='button-gray action-button'>
                  Cancel
                </div>
                <div onClick={this.handleSubmit.bind(this)} className='button-blue action-button ml-3'>
                  Retry
                </div>
            </div>
          </div>
      } else if (this.state.message_type == 'success') {
        var json = JSON.parse(this.state.message);
        visible =
          <div>
            <div className="import-github-success">
              Successfully imported {json.author} module "{json.name}" under category "{json.category}".
            </div>
            <div className="modal-solo-button">
              <div onClick={this.toggleModal} className='button-blue action-button mt-5'>
                OK
              </div>
            </div>
          </div>
      }
    } else {
      visible =
        <div className="modal-dual-button d-flex flex-row">
          <div onClick={this.toggleModal} className='button-gray action-button'>
            Cancel
          </div>
          <div onClick={this.handleSubmit.bind(this)} className='button-blue action-button ml-3'>
            Import
          </div>
        </div>
    };


    return (
      <div>

        <div className='import-module-button content-3 mb-5 t-vl-gray' onClick={ this.toggleModal }>
          IMPORT FROM GITHUB
        </div>;

        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className='modal-dialog'>
          <ModalHeader toggle={this.toggleModal} >
            <div className='title-4 t-d-gray'>Import from GitHub</div>
          </ModalHeader>
          <ModalBody className='dialog-body'>
            <form onSubmit={this.handleSubmit}>
              <div className="label-margin t-d-gray content-3">Git Url:</div>
              <div className="import-url-field">
                <input type="text"
                      className="text-field mb-3 mt-2 content-3"
                      value={this.state.value}
                      placeholder='https://github.com/...'
                      onChange={this.handleChange}
                      onKeyPress={this.handleChange}
                      />
              <div className="label-margin t-m-gray info-1">Learn more about how to build your own module <a href="http://cjworkbench.org/index.php/build-a-module/" className=' t-f-blue'>here</a></div>
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
  moduleAdded: PropTypes.func.isRequired
};
