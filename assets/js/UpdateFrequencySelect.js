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

  // --- Takes a date string, returns the interval of time between now and then ---
  // --- Won't work until this component has date information ---
  // timeDiff(datestr) {
  //   // interpret date string as UTC always (comes from server this way)
  //   var d = new Date(datestr);
  //   var now = new Date();
  //   var interval = now.getTime() - d.getTime();
  //   var days = Math.floor(interval/864000000);
  //   var hours = Math.floor((interval - days*864000000)/3600000);
  //   var minutes = Math.floor((interval - days*864000000 - hours*3600000)/60000);
  //   if (days > 1) {
  //     return "" + days + " days ago";
  //   } else if (days == 1) {
  //     return "1 day ago";
  //   } else if (hours > 1) {
  //     return "" + hours + "hours ago";
  //   } else if (hours == 1) {
  //     return "1 hour ago";
  //   } else if (minutes > 1) {
  //     return "" + minutes + "minutes ago";
  //   } else {
  //     return "just now";
  //   }
  // }

  render() {

    var highlightManual = this.state.manual ? 'action-button button-blue' : 'action-button button-gray';
    var highlightAuto = !this.state.manual ? 'action-button button-blue' : 'action-button button-gray';
    var settingsInfo = this.state.manual ?
      'Manual'
      :'Auto, every ' + this.state.period + ' ' + this.state.unit;
    if (this.state.period > 1) {
      settingsInfo += 's';
    }

    return (
      <div className='version-item'>
        <div className='mb-2' >
          <span className='info-medium-gray'>Update: </span>
          <span className='info-medium-blue' onClick={this.toggleModal}>{settingsInfo}</span>  
        </div>
         <div className='info-medium-light-gray'>Click above to change</div>         
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className={this.props.className}>
          <ModalHeader toggle={this.toggleModal} className='dialog-box-title-gray'>Sync Settings</ModalHeader>
          <ModalBody>
            <FormGroup>
              <Label for="updateFreq" className=''>Check for update every</Label>
              <div className='update-freq-settings update-freq-test-class'>
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
          </ModalBody>
          <ModalFooter>
            <Button className='action-button button-blue' onClick={this.toggleModal}>Apply</Button>
          </ModalFooter>
        </Modal>
      </div>
    );
  }

}
