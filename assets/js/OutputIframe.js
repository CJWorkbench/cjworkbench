import React from 'react'
import IframeCtrl from './IframeCtrl'
import {Modal, ModalBody, ModalHeader} from 'reactstrap'
import {store, setWorkflowPublicAction} from "./workflow-reducer";
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
    let iframeCode = '<iframe src="' + window.location.host + '/embed/' + this.props.selectedWfModuleId + '" />';
    iframeCode
     .replace(/&/g, "&amp;")
     .replace(/</g, "&lt;")
     .replace(/>/g, "&gt;")
     .replace(/"/g, "&quot;")
     .replace(/'/g, "&#039;");

    return (
      <Modal isOpen={this.state.embedIframeModalOpen} toggle={this.toggleModals} className='test-setpublic-modal'>
        <ModalHeader toggle={this.toggleModals} className='dialog-header modal-header d-flex align-items-center' >
          <div className='t-d-gray title-4'>EMBED THIS WORKFLOW</div>
        </ModalHeader>
        <ModalBody className='dialog-body'>
          <pre>
            <code>
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

export {OutputIframe, OutputIframeCtrl}
