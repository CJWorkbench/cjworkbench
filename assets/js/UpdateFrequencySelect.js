import React from 'react'
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import { Form, FormGroup, Label, Input } from 'reactstrap'

export default class UpdateFrequencySelect extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      modalOpen: false,
      manual: true
    };
    this.toggleModal = this.toggleModal.bind(this);
    this.toggleManual = this.toggleManual.bind(this);    
  }

  toggleModal() {
    this.setState({ modalOpen: !this.state.modalOpen });
  }

  toggleManual() {
    this.setState({ manual: !this.state.manual });
  }

  render() {
    var highlightManual = this.state.manual ? 'button-blue' : 'button-gray';
    var highlightAuto = !this.state.manual ? 'button-blue' : 'button-gray';    

    return (
      <div className='version-item'>
        <div className='info-blue mb-2' onClick={this.toggleModal}>Set Update Frequency</div>
        <div className=''>Checked for update: X ago</div>
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className={this.props.className}>
          <ModalHeader toggle={this.toggleModal}>Sync Settings</ModalHeader>
          <ModalBody>
            <FormGroup>
              <Label for="updateFreq">Check for update every</Label>
              <Input type="number" min='1' placeholder='1' name="updateFreq" id="updateFreqNum"></Input>
              <Input type="select" name="updateFreq" id="updateFreqPeriod">
                <option>Hour</option>
                <option>Day</option>                
                <option>Week</option>
                <option>Month</option>
              </Input>
              <div>When an update is found:</div>
              <Button onClick={this.toggleManual} className={highlightManual} >Manual</Button>
              <div>Do not automatically switch to latest data (recommended)</div>              
              <Button onClick={this.toggleManual} className={highlightAuto}>Auto</Button>
              <div>Saves currect data and automatically uses the latest data</div>              
            </FormGroup>
          </ModalBody>’
          <ModalFooter>
            {/*Currently this button only closes the Modal window, does not change settings*/}
            <Button color='secondary' onClick={this.toggleModal}>Apply</Button>
          </ModalFooter>
        </Modal>
      </div>
    );
  }

}
