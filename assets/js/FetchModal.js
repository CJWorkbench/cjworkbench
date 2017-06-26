// Button that pops up a modal with fetch parameters

import React from 'react'
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import { Form, FormGroup, Label, Input } from 'reactstrap'


export default class FetchModal extends React.Component {
  constructor(props) {
    super(props);
    this.state = { modal: false };
    this.toggleModal = this.toggleModal.bind(this);
  }

  toggleModal() {
    this.setState({ modal: !this.state.modal });
  }

  render() {
    return (
      <span className="ml-2">
        <Button color='secondary' onClick={this.toggleModal}> {'\u23F1'} </Button>
        <Modal isOpen={this.state.modal} toggle={this.toggleModal} className={this.props.className}>
          <ModalHeader toggle={this.toggleModal}>External Data Settings</ModalHeader>
          <ModalBody>
            <FormGroup>
              <Label for="exampleSelect">Which version?</Label>
              <Input type="select" name="select" id="exampleSelect" className="mb-3">
                <option>Most Recent</option>
                <option value="" disabled="disabled">──────────</option>
                <option>April 28 at 4:40PM </option>
                <option>April 28 at 10:32AM </option>
                <option>April 26 at 6:06PM</option>
                <option>April 12 at 2:51PM</option>
              </Input>
              <Label for="exampleSelect2">Update when?</Label>
              <Input type="select" name="select" id="exampleSelect2">
                <option>Manual only</option>
                <option value="" disabled="disabled">──────────</option>
                <option>Every minute</option>
                <option>Every five minutes</option>
                <option>Hourly</option>
                <option>Daily</option>
                <option>Weekly</option>
              </Input>
            </FormGroup>
          </ModalBody>
          <ModalFooter>
            <Button color='primary' onClick={this.toggleModal}>Ok</Button>{' '}
            <Button color='secondary' onClick={this.toggleModal}>Cancel</Button>
          </ModalFooter>
        </Modal>
      </span>
    );
  }
}

