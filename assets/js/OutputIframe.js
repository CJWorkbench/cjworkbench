import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './components/Modal'
import { setWfModuleParamsAction } from './workflow-reducer'
import { setWorkflowPublicAction } from './ShareModal/actions'
import { connect } from 'react-redux'
import { escapeHtml } from './utils'

export class OutputIframe extends React.PureComponent {
  static propTypes = {
    visible: PropTypes.bool.isRequired, // false means, "zero height"
    deltaId: PropTypes.number, // null if added to empty workflow
    wfModuleId: PropTypes.number, // null if no wfmodule
    isPublic: PropTypes.bool.isRequired,
    workflowId: PropTypes.number.isRequired,
  }

  state = {
    heightFromIframe: null, // if set, the iframe told us how tall it wants to be
    isModalOpen: false,
  }

  componentDidUpdate(prevProps, prevState) {
    if (prevProps.wfModuleId !== this.props.wfModuleId) {
      this.setState({
        heightFromIframe: null
      })
    }

    if (prevState.heightFromIframe !== this.state.heightFromIframe || prevProps.visible !== this.props.visible) {
      const resizeEvent = document.createEvent('Event')
      resizeEvent.initEvent('resize', true, true)
      window.dispatchEvent(resizeEvent)
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
      if (data.wfModuleId !== this.props.wfModuleId) {
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
        case 'set-params':
          this.props.setWfModuleParams(data.wfModuleId, data.params)
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
      <Modal isOpen={this.isModalOpen('public')} toggle={this.closeModal}>
        <ModalHeader toggle={this.closeModal}>
          <div className='modal-title'>SHARE THIS WORKFLOW</div>
        </ModalHeader>
        <ModalBody>
          <div className='title-3 mb-3'>This workflow is currently private</div>
          <div className='info-3 t-d-gray'>Set this workflow to Public in order to share it? Anyone with the URL will be able to access and duplicate it.</div>
        </ModalBody>
        <ModalFooter>
          <div onClick={this.closeModal} className='button-gray action-button mr-4'>Cancel</div>
          <div onClick={this.props.setWorkflowPublic} className='button-blue action-button test-public-button'>Set public</div>
        </ModalFooter>
      </Modal>
    )
  }

  renderEmbedModal () {
    let iframeCode = escapeHtml('<iframe src="' + window.location.protocol + '//' + window.location.host + '/embed/' + this.props.wfModuleId + '" width="560" height="315" frameborder="0" />')

    return (
      <Modal isOpen={this.isModalOpen('embed')} toggle={this.closeModal}>
        <ModalHeader toggle={this.closeModal}>
          <div className='modal-title'>EMBED THIS CHART</div>
        </ModalHeader>
        <ModalBody>
          <p className='info'>Paste this code into any webpage HTML</p>
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
    const { wfModuleId, deltaId, visible } = this.props
    const { heightFromIframe } = this.state
    const src = `/api/wfmodules/${wfModuleId}/output#revision=${deltaId}`

    const defaultHeight = visible ? '100%' : '0'
    const height = heightFromIframe === null ? defaultHeight : `${Math.ceil(heightFromIframe)}px`

    return (
      <div className='outputpane-iframe' style={{ height }}>
        { !visible ? null : (
          <React.Fragment>
            <iframe src={src} />
            <div className='outputpane-iframe-control-overlay'>
              <button name='embed' className='btn' title='Get an embeddable URL' onClick={this.openModal}>
                <i className='icon icon-code' />
              </button>
            </div>
            {this.renderPublicModal()}
            {this.renderEmbedModal()}
          </React.Fragment>
        )}
      </div>
    )
  }
}

const mapStateToProps = (state) => ({})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    setWorkflowPublic: () => {
      dispatch(setWorkflowPublicAction(true))
    },
    setWfModuleParams: (wfModuleId, params) => {
      dispatch(setWfModuleParamsAction(wfModuleId, params))
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(OutputIframe)
