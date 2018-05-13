import React from 'react'
import { csrfToken } from '../utils'
import { Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'

export default class FileSelect extends React.Component {
    constructor(props) {
      super(props);
      var savedFileMeta = this.props.getState();
      if (savedFileMeta !== '') {
        savedFileMeta = JSON.parse(savedFileMeta);
      } else {
        savedFileMeta = false;
      }
      this.state = {
        files: [],
        file: savedFileMeta,
        modalOpen: false
      }
      this.toggleModal = this.toggleModal.bind(this);
    }

    getFiles() {
      return this.props.api.postParamEvent(
        this.props.pid,
        { type: 'fetchFiles' }
      ).then(result => {
        this.setState({files: result.files});
      });
    }

    componentDidMount() {
      if (this.props.userCreds.length > 0) {
        this.getFiles()
      }
    }

    componentDidUpdate(prevProps) {
      if (this.props.userCreds.length > 0 && this.props.userCreds[0] !== prevProps.userCreds[0]) {
        this.getFiles()
      }

      if (this.props.userCreds.length === 0) {
        this.setState({
          files: []
        })
      }
    }

    handleClick(file) {
      this.props.api.postParamEvent(
        this.props.pid,
        {
          file: file,
          type: 'fetchFile'
        }
      ).then((response) => {
          this.props.saveState(JSON.stringify(file));
          this.setState({file: file});
          this.toggleModal();
        }
      );
    }

    toggleModal() {
      this.setState({ modalOpen: !this.state.modalOpen });
    }

    render() {
      let fileList = null
      let filesModal = null
      let fileInfo = null

      if (typeof this.state.files !== 'undefined' && this.state.files.length > 0) {

        fileList = (this.state.files.map( (file, idx) => {
          return (
            <div className="line-item--data-version" key={idx} onClick={() => this.handleClick(file)}>
              <span className="content-3">{file.name}</span>
            </div>
          );
        }));

        filesModal = (
          <div>
            {!this.state.file &&
              <div className="button-orange action-button mt-0" onClick={this.toggleModal}>Choose</div>}
              <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal}>
                <ModalHeader toggle={this.toggleModal}>
                  <div className='title-4 t-d-gray'>Choose File</div>
                </ModalHeader>
                <ModalBody className="list-body">
                  <div >
                    {fileList}
                  </div>
                </ModalBody>
                <div className=" modal-footer"></div>
              </Modal>
          </div>
        );
      }

      if (this.state.file) {
        fileInfo = (
          <div>
            <div className="d-flex">
              <div className={"t-d-gray content-3 label-margin"}>File</div>
              {this.state.files.length > 0 &&
              <div onClick={this.toggleModal} className="t-f-blue ml-2">Change</div>}
            </div>
            <div><span className={"t-d-gray content-3 mb-3"}>{this.state.file.name}</span></div>
          </div>
        )
      } else if (fileList) {
        fileInfo = (
          <p>{this.state.files.length} files found</p>
        )
      }

      if (fileInfo) {
        return (
          <div className="parameter-margin">
            <div className={"parameter-margin d-flex gdrive-fileSelect align-items-center"}>
              <div className={"file-info content-3"}>
                {fileInfo}
              </div>
              {filesModal}
            </div>
          </div>
        );
      } else {
        return null
      }

    }
}
