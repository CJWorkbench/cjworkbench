/**
 * Component that handles the Import from GitHub functionality. This functionality allows users
 * to insert a URL to a GitHub repository in a textfield, and, if there are no errors,
 * a new module is added to the Module Library.
 *
 */

import React from 'react'
import { Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import PropTypes from 'prop-types'
import { loadModulesAction } from './workflow-reducer'
import {connect} from "react-redux";

class Button extends React.PureComponent {
  render() {
    const { onClick, color, name, children } = this.props

    return <button name={name} className={`action-button button-${color}`} onClick={onClick}>{children}</button>
  }
}
Button.propTypes = {
  onClick: PropTypes.func.isRequired,
  color: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  extraClassName: PropTypes.string,
}

export class ImportModuleFromGitHub extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      url: '',
      message_type: '',
      message: null
    };
    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.onKeyPress = this.keyPress.bind(this); // to handle user hitting enter, which then submits
    this.handleResponse = this.handleResponse.bind(this);
  }

  keyPress(event) {
    event.preventDefault(); // stops the page from refreshing
    if (e.key == 'Enter') {
      handleSubmit(event);``
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
    var eventData = {'url': this.state.url};
    this.props.api.importFromGithub(eventData)
      .then(
        (json) => {
          this.handleResponse(json);
          this.props.reloadModules();
        },
        (error) => {
          this.handleResponse(null); // 500 error
        }
      );
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

  render() {

    var formContent = null;
    var footer = null;

    if (this.state.message) {
      if (this.state.message_type == 'error') {
        formContent = (
          <div>
            <div className="import-github-error">
              <div>{this.state.message}</div>
            </div>
          </div>
        )
        footer = (
          <React.Fragment>
            <Button onClick={this.props.closeModal} color="gray" name="cancel">Cancel</Button>
            <Button onClick={this.handleSubmit} color="blue" name="retry">Retry</Button>
          </React.Fragment>
        )
      } else if (this.state.message_type == 'success') {
        var json = JSON.parse(this.state.message);
        formContent = (
          <div>
            <div className="import-github-success">
              Successfully imported {json.author} module "{json.name}" under category "{json.category}".
            </div>
          </div>
        )
        footer = (
          <Button onClick={this.props.closeModal} color="blue" name="ok">OK</Button>
        )
      }
    } else {
      footer = (
        <React.Fragment>
          <Button onClick={this.props.closeModal} color="gray" name="cancel">Cancel</Button>
          <Button onClick={this.handleSubmit} color="blue" name="import">Import</Button>
        </React.Fragment>
      )
    };

    return (
      <div >
        <Modal isOpen={true} className='modal-dialog'>
          <ModalHeader>
            <div className='title-4 t-d-gray'>IMPORT CUSTOM MODULE</div>
          </ModalHeader>
          <ModalBody >
            <form onSubmit={this.handleSubmit}>
              <div className="label-margin t-d-gray content-3">GIT URL</div>
              <div className="import-url-field">
                <input type="text"
                      className="text-field mb-3 mt-2 content-3"
                      value={this.state.value}
                      placeholder='https://github.com/...'
                      onChange={this.handleChange}
                      onKeyPress={this.handleChange}
                      />
              <div className="label-margin t-m-gray info-1">Learn more about how to build your own module <a target="_blank" href=" https://github.com/CJWorkbench/cjworkbench/wiki/Creating-A-Module" className=' t-f-blue'>here</a></div>
              </div>
              {formContent}
            </form>
          </ModalBody>
          <ModalFooter>{footer}</ModalFooter>
        </Modal>

      </div>
    );
  }
}


ImportModuleFromGitHub.propTypes = {
  closeModal:  PropTypes.func.isRequired,
  api:         PropTypes.object.isRequired,
};

const mapDispatchToProps = {
  reloadModules: loadModulesAction
};

export default connect(
  null,
  mapDispatchToProps
)(ImportModuleFromGitHub);
