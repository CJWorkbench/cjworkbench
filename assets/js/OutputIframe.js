import React from 'react'
import PropTypes from 'prop-types'
import IframeCtrl from './IframeCtrl'
import {Modal, ModalBody, ModalHeader} from 'reactstrap'
import {store, setWorkflowPublicAction} from "./workflow-reducer"
import {escapeHtml} from "./utils";
let OutputIframeCtrl;

class OutputIframe extends React.Component {
  constructor(props) {
    super(props);
    this.toggleModal = this.toggleModal.bind(this);
    this.toggleSetPublicModal = this.toggleSetPublicModal.bind(this);
    this.toggleEmbedIframeModal = this.toggleEmbedIframeModal.bind(this);
    this.setPublic = this.setPublic.bind(this);
    this.state = {
      src: ("/api/wfmodules/" + this.props.selectedWfModuleId + "/output?rev=" + this.props.revision),
      setPublicModalOpen: false,
      embedIframeModalOpen: false
    }
  }

  componentWillReceiveProps(nextProps) {
    this.setState({
      src: ("/api/wfmodules/" + nextProps.selectedWfModuleId + "/output?rev=" + nextProps.revision)
    });
    if (this.state.setPublicModalOpen
      && nextProps.workflow.public
      && (nextProps.workflow.public !== this.props.workflow.public)) {
      this.toggleSetPublicModal();
      this.toggleEmbedIframeModal();
    }
  }

  setRef(ref) {
    OutputIframeCtrl = new IframeCtrl(ref);
  }

  toggleSetPublicModal() {
    this.setState({
      setPublicModalOpen: !this.state.setPublicModalOpen
    })
  }

  toggleEmbedIframeModal() {
    this.setState({
      embedIframeModalOpen: !this.state.embedIframeModalOpen
    });
  }

  toggleModal() {
    if (!this.props.workflow.public) {
      this.toggleSetPublicModal();
    } else {
      this.toggleEmbedIframeModal();
    }
  }

  setPublic() {
    store.dispatch(setWorkflowPublicAction(this.props.workflow.id, true));
  }

  renderSetPublicModal() {
    return (
      <Modal isOpen={this.state.setPublicModalOpen} toggle={this.toggleModals} className='test-setpublic-modal'>
        <ModalHeader toggle={this.toggleModals} className='dialog-header modal-header d-flex align-items-center' >
          <div className='t-d-gray title-4'>SHARE THIS WORKFLOW</div>
        </ModalHeader>
        <ModalBody className='dialog-body'>
          <div className='title-3 mb-3'>This workflow is currently private</div>
          <div className='info-2 t-d-gray'>Set this workflow to Public in order to share it? Anyone with the URL will be able to access and duplicate it.</div>
        </ModalBody>
        <div className="modal-footer dialog-footer">
          <div onClick={this.toggleSetPublicModal} className='button-gray action-button mr-4'>Cancel</div>
          <div onClick={this.setPublic} className='button-blue action-button test-public-button'>Set Public</div>
        </div>
      </Modal>
    )
  }

  renderEmbedCodeModal() {
    let iframeCode = escapeHtml('<iframe src="' + window.location.host + '/embed/' + this.props.selectedWfModuleId + '" />');

    return (
      <Modal isOpen={this.state.embedIframeModalOpen} toggle={this.toggleModals} className='test-setpublic-modal'>
        <ModalHeader toggle={this.toggleModals} className='dialog-header modal-header d-flex align-items-center' >
          <div className='t-d-gray title-4'>EMBED THIS WORKFLOW</div>
        </ModalHeader>
        <ModalBody className='dialog-body'>
          <pre>
            <code className="content-3 t-d-gray">
              {iframeCode}
            </code>
          </pre>
        </ModalBody>
        <div className="modal-footer dialog-footer">
          <div onClick={this.toggleEmbedIframeModal} className='button-gray action-button mr-4'>OK</div>
        </div>
      </Modal>
    )
  }

  render() {
    return (
      <div className="outputpane-iframe">
        {this.renderSetPublicModal()}
        {this.renderEmbedCodeModal()}
        <div className="outputpane-iframe-control-overlay">
          <div className="btn icon icon-code" onClick={this.toggleModal} />
        </div>
        <iframe ref={this.setRef} src={this.state.src} />
      </div>
    );
  }
}

OutputIframe.propTypes = {
  id: PropTypes.number.isRequired,
  revision: PropTypes.number,
  api: PropTypes.object.isRequired,
  selectedWfModuleId: PropTypes.number.isRequired,
  workflow: PropTypes.object.isRequired,

}

export {OutputIframe, OutputIframeCtrl}
