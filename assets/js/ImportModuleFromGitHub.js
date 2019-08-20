import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './components/Modal'
import { updateModuleAction } from './workflow-reducer'
import { connect } from 'react-redux'

class StaffImportModuleFromGitHub extends React.PureComponent {
  static propTypes = {
    closeModal: PropTypes.func.isRequired,
    api: PropTypes.shape({
      importModuleFromGitHub: PropTypes.func.isRequired // func(url) => Promise[moduleObject or Error]
    }).isRequired,
    addModuleToState: PropTypes.func.isRequired // func(moduleObject) => undefined
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
        message: `Imported module "${data.name}" under category "${data.category}"`
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

  render () {
    const { status } = this.state

    return (
      <Modal isOpen toggle={this.props.closeModal}>
        <ModalHeader toggle={this.props.closeModal}>Import Custom Module</ModalHeader>
        <ModalBody>
          <form id='import-from-github-form' onSubmit={this.handleSubmit}>
            <div className='import-url-field'>
              <input
                name='url'
                type='url'
                className='text-field mb-3 mt-2 content-1'
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
              Learn about how to build your own module
              {' '}<a target='_blank' rel='noopener noreferrer' href='https://github.com/CJWorkbench/cjworkbench/wiki/Creating-A-Module' className='action-link'>here</a>
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

function PublicImportModuleFromGitHub ({ closeModal }) {
  return (
    <Modal isOpen toggle={closeModal}>
      <ModalHeader toggle={closeModal}>Import Custom Module</ModalHeader>
      <ModalBody>
        <div className='label-margin t-m-gray info-1'>
          Learn about how to build your own module
          {' '}<a target='_blank' rel='noopener noreferrer' href='https://github.com/CJWorkbench/cjworkbench/wiki/Creating-A-Module' className='action-link'>here</a>
        </div>
      </ModalBody>
      <ModalFooter>
        <button type='button' className='action-button button-blue' name='close' onClick={closeModal}>Close</button>
      </ModalFooter>
    </Modal>
  )
}

export function ImportModuleFromGitHub ({ isStaff, ...innerProps }) {
  const Component = isStaff ? StaffImportModuleFromGitHub : PublicImportModuleFromGitHub
  return <Component {...innerProps} />
}
ImportModuleFromGitHub.propTypes = {
  closeModal: PropTypes.func.isRequired,
  isStaff: PropTypes.bool.isRequired,
  api: PropTypes.shape({
    importModuleFromGitHub: PropTypes.func.isRequired // func(url) => Promise[moduleObject or Error]
  }).isRequired,
  addModuleToState: PropTypes.func.isRequired // func(moduleObject) => undefined
}

const mapStateToProps = (state) => ({
  isStaff: state.loggedInUser.is_staff
})

const mapDispatchToProps = {
  addModuleToState: updateModuleAction
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ImportModuleFromGitHub)
