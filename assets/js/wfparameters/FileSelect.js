import React from 'react'
import { csrfToken } from '../utils'
import { Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'

export default class FileSelect extends React.Component {
    constructor(props) {
      super(props);
      this.state = {
        files: [],
        file: JSON.parse(this.props.getState()),
        modalOpen: false
      }
      this.toggleModal = this.toggleModal.bind(this);
    }

    getFiles() {
      var url = '/api/parameters/'+this.props.ps.id+'/event';
      fetch(url, {
        method: 'get',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        }
      })
      .then(result => result.json())
      .then(result => {
        this.setState({files: result.files});
      });
    }

    componentDidMount() {
      this.getFiles();
    }

    componentWillReceiveProps() {
      this.getFiles();
    }

    handleClick(file) {
      var url = '/api/parameters/'+this.props.ps.id+'/event';
      fetch(url, {
        method: 'post',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(file)
      })
      .then(() => {
          this.props.saveState(JSON.stringify(file));
          this.setState({file:file});
        }
      );
    }

    toggleModal() {
      this.setState({ modalOpen: !this.state.modalOpen });
    }

    render() {
      console.log('fileselect rerendered');
      var fileList, filesModal;
      console.log(this.state);
      fileList = (this.state.files.map( (file, idx) => {
        return (
          <div className="line-item-data" key={idx} onClick={() => this.handleClick(file)}>
            <span class="content-3">{file.name}</span>
          </div>
        );
      }));
      filesModal = (
        <div className="parameter-margin">
          <p>Selected file: {this.state.file.name}</p>
          <p>{this.state.files.length} files found.</p>
          <div className="button-blue action-button mt-0" onClick={this.toggleModal}>Choose file</div>
          <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal}>
            <ModalHeader toggle={this.toggleModal}>
              <div className='title-4 t-d-gray'>Choose File</div>
            </ModalHeader>
            <ModalBody className="dialog-body">
              <div className="scrolling-list">
                {fileList}
              </div>
            </ModalBody>
          </Modal>
        </div>
      );
      return filesModal;
    }
}
