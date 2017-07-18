import React from 'react'
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import { Form, FormGroup, Label, Input } from 'reactstrap'

export default class UpdateFrequencySelect extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      modalOpen: false,
      manual: true,
      period: 1,
      unit: 'Day'
    };
    this.toggleModal = this.toggleModal.bind(this);
    this.toggleManual = this.toggleManual.bind(this);  
    this.updatePeriod = this.updatePeriod.bind(this);    
    this.updateUnit = this.updateUnit.bind(this);    
      
  }

  toggleModal() {
    this.setState(
      Object.assign({}, this.state, {modalOpen: !this.state.modalOpen })
    )
  }

  toggleManual() {
    this.setState(
      Object.assign({}, this.state, {manual: !this.state.manual})
    )
  }

  updatePeriod(event) {
    this.setState(
      Object.assign({}, this.state, {period: event.target.value})
    );
  }

  updateUnit(event) {
    this.setState(
      Object.assign({}, this.state, {unit: event.target.value})
    );
  }

  render() {

    var highlightManual = this.state.manual ? 'action-button-active' : 'action-button-disabled';
    var highlightAuto = !this.state.manual ? 'action-button-active' : 'action-button-disabled';
    var settingsInfo = this.state.manual ?
      'Update Settings: Manual'
      : 'Update Settings: Auto, every ' + this.state.period + ' ' + this.state.unit;

    return (
      <div className='version-item'>
        <div className='info-blue mb-2' onClick={this.toggleModal}>Update Frequency</div>
        <div className=''>{settingsInfo}</div>
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className={this.props.className}>
          <ModalHeader toggle={this.toggleModal}>Sync Settings</ModalHeader>
          <ModalBody>
            <FormGroup>
              <Label for="updateFreq">Check for update every</Label>
              <div className='update-freq-settings'>
                <Input 
                  type="number" 
                  value={this.state.period} 
                  onChange={this.updatePeriod}
                  min='1' 
                  max='100' 
                  name="updateFreq" 
                  id="updateFreqNum">
                </Input>
                <Input 
                  type="select" 
                  value={this.state.unit} 
                  onChange={this.updateUnit}
                  name="updateFreq" 
                  id="updateFreqPeriod" 
                  className='ml-1'
                >
                  <option>Hour</option>
                  <option>Day</option>                
                  <option>Week</option>
                  <option>Month</option>
                </Input>
              </div>
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
