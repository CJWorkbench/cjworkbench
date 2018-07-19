import React from 'react'
import PropTypes from 'prop-types'
import Modal from 'reactstrap/lib/Modal'
import ModalHeader from 'reactstrap/lib/ModalHeader'
import ModalBody from 'reactstrap/lib/ModalBody'
import { setWorkflowPublicAction } from './workflow-reducer'
import { connect } from 'react-redux'
import { escapeHtml } from './utils'

export let OutputIframeCtrl

export class OutputIframe extends React.PureComponent {
  static propTypes = {
    revision: PropTypes.number, // null if added to empty workflow
    selectedWfModuleId: PropTypes.number.isRequired,
    isPublic: PropTypes.bool.isRequired,
    workflowId: PropTypes.number.isRequired,
  }

  // TODO nix this, nix postMessage entirely. HTML should watch for hash
  // change in URL for the forseeable future.
  hackySetIframe = (iframe) => {
    OutputIframeCtrl = iframe ? iframe.contentWindow : null
  }

  state = {
    heightFromIframe: null, // if set, the iframe told us how tall it wants to be
    gotInitFromIframe: null, // if set, iframe told us it will send messages
    isModalOpen: false,
  }

  componentDidUpdate(prevProps) {
    if (prevProps.selectedWfModuleId !== this.props.selectedWfModuleId) {
      this.setState({
        heightFromIframe: null,
        gotInitFromIframe: null,
      })
    }
  }

  componentDidMount() {
    window.addEventListener('message', this.onMessage)
  }

  componentWillUnmount() {
    window.removeEventListener('message', this.onMessage)
  }

  onMessage = (ev) => {
    const data = ev.data
    if (data && data.from === 'outputIframe') {
      if (data.wfModuleId !== this.props.selectedWfModuleId) {
        // This message isn't from the iframe we created.
        //
        // This check works around a race:
        //
        // 1. Show an iframe
        //    ... it sends a 'resize' event
        //    ... it keeps sending 'resize' events whenever its size changes
        // 2. Switch to a different iframe src
        //    ... this resets size and sets new iframe src; BUT before the new
        //        iframe can load, the _old_ iframe's JS sends a 'resize' event
        //
        // By forcing the iframe to send its identity, we can make sure this
        // message isn't spurious.
        return
      }

      switch (data.type) {
        case 'resize':
          this.setState({ heightFromIframe: data.height })
          break
        default:
          console.error('Unhandled message from iframe', data)
      }
    }
  }

  toggleSetPublicModal = () => {
    this.setState({
      setPublicModalOpen: !this.state.setPublicModalOpen
    })
  }

  toggleEmbedIframeModal () {
    this.setState({
      embedIframeModalOpen: !this.state.embedIframeModalOpen
    })
  }

  openModal = () => {
    this.setState({ isModalOpen: true })
  }

  closeModal = () => {
    this.setState({ isModalOpen: false })
  }

  isModalOpen (name) {
    if (!this.state.isModalOpen) return false
    if (this.props.isPublic) {
      return name === 'embed'
    } else {
      return name === 'public'
    }
  }

  renderPublicModal () {
    return (
      <Modal isOpen={this.isModalOpen('public')} toggle={this.closeModal} className='test-setpublic-modal'>
        <ModalHeader toggle={this.closeModal} className='dialog-header modal-header d-flex align-items-center'>
          <div className='modal-title'>SHARE THIS WORKFLOW</div>
        </ModalHeader>
        <ModalBody >
          <div className='title-3 mb-3'>This workflow is currently private</div>
          <div className='info-2 t-d-gray'>Set this workflow to Public in order to share it? Anyone with the URL will be able to access and duplicate it.</div>
        </ModalBody>
        <div className='modal-footer'>
          <div onClick={this.closeModal} className='button-gray action-button mr-4'>Cancel</div>
          <div onClick={this.props.setWorkflowPublic} className='button-blue action-button test-public-button'>Set Public</div>
        </div>
      </Modal>
    )
  }

  renderEmbedModal () {
    let iframeCode = escapeHtml('<iframe src="' + window.location.protocol + '//' + window.location.host + '/embed/' + this.props.selectedWfModuleId + '" width="560" height="315" frameborder="0" />')

    return (
      <Modal isOpen={this.isModalOpen('embed')} toggle={this.closeModal} className='test-setpublic-modal'>
        <ModalHeader toggle={this.closeModal} className='dialog-header modal-header d-flex align-items-center'>
          <div className='modal-title'>EMBED THIS CHART</div>
        </ModalHeader>
        <ModalBody >
          <span className='info'>Paste this code into any webpage HTML</span>
          <div className='code-snippet'>
            <code className='chart-embed'>
              {iframeCode}
            </code>
          </div>
        </ModalBody>
        <div className='modal-footer'>
          <div onClick={this.closeModal} className='button-gray action-button'>OK</div>
        </div>
      </Modal>
    )
  }

  render () {
    const { selectedWfModuleId, revision } = this.props
    const { heightFromIframe } = this.state
    const src = `/api/wfmodules/${selectedWfModuleId}/output#revision=${revision}`

    const height = heightFromIframe === null ? '100%' : `${Math.ceil(heightFromIframe)}px`

    return (
      <div className='outputpane-iframe' style={{ height }}>
        <iframe ref={this.hackySetIframe} src={src} />
        <div className='outputpane-iframe-control-overlay'>
          <button name='embed' className='btn' title='Get an embeddable URL' onClick={this.openModal}>
            <i className='icon icon-code' />
          </button>
        </div>
        {this.renderPublicModal()}
        {this.renderEmbedModal()}
      </div>
    )
  }
}

const mapStateToProps = (state) => ({})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    setWorkflowPublic: () => {
      dispatch(setWorkflowPublicAction(ownProps.workflowId, true))
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(OutputIframe)
