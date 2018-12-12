import React from 'react'
import PropTypes from 'prop-types'
import Modal from 'reactstrap/lib/Modal'
import ModalHeader from 'reactstrap/lib/ModalHeader'
import ModalBody from 'reactstrap/lib/ModalBody'
import ModalFooter from 'reactstrap/lib/ModalFooter'
import { updateModuleAction } from './workflow-reducer'
import { connect } from 'react-redux'

export class ImportModuleFromGitHub extends React.Component {
  static propTypes = {
    closeModal: PropTypes.func.isRequired,
    api: PropTypes.shape({
      importModuleFromGitHub: PropTypes.func.isRequired // func(url) => Promise[moduleObject or Error]
    }).isRequired,
    addModuleToState: PropTypes.func.isRequired, // func(moduleObject) => undefined
  }

  state = {
    status: { message: '', error: null }
  }

  inputRef = React.createRef()

  handleSubmit = (ev) => {
    ev.preventDefault() // don't submit browser-default GET/POST

    this.setState({
      status: { message: 'Processing...' }
    })

    const url = this.inputRef.current.value
    this.props.api.importModuleFromGitHub(url)
      .then(this.onImportSuccess, this.onImportFailure)
  }

  onImportSuccess = (data) => {
    this.props.addModuleToState(data)
    this.setState({
      status: {
        message: `Imported ${data.author} module "${data.name}" under category "${data.category}"`
      }
    })
  }

  onImportFailure = (error) => {
    this.setState({
      status: {
        error: error.message
      }
    })
  }

  render() {
    const { status } = this.state

    return (
      <Modal isOpen={true} toggle={this.props.closeModal}>
        <ModalHeader toggle={this.props.closeModal}>Import Custom Module</ModalHeader>
        <ModalBody>
          <form id='import-from-github-form' onSubmit={this.handleSubmit}>
            <div className='import-url-field'>
              <input
                name='url'
                type='url'
                className='text-field mb-3 mt-2 content-3'
                ref={this.inputRef}
                placeholder='https://github.com/user/repo.git'
              />
            </div>
            {status.message ? (
              <div className='import-github-success'>{status.message}</div>
            ) : null}
            {status.error ? (
              <div className='import-github-error'>{status.error}</div>
            ) : null}
            <div className='label-margin t-m-gray info-1'>
              Learn more about how to build your own module
              <a target='_blank' href='https://github.com/CJWorkbench/cjworkbench/wiki/Creating-A-Module' className='action-link'>here</a>
            </div>
          </form>
        </ModalBody>
        <ModalFooter>
          <button type='submit' className='action-button button-blue' name='import' form='import-from-github-form'>Import</button>
        </ModalFooter>
      </Modal>
    )
  }
}

const mapDispatchToProps = {
  addModuleToState: updateModuleAction
}

export default connect(
  null,
  mapDispatchToProps
)(ImportModuleFromGitHub)
