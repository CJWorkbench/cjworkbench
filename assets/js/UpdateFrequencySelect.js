import React from 'react'
import PropTypes from 'prop-types'
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
         <div className='info-medium-light-gray'>Last checked: {this.props.lastUpdateCheck}</div>
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal}>
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
              <div>
                <Button onClick={this.toggleManual} className={highlightManual} >Manual</Button>
                <div className=''>Do not automatically switch to latest data (recommended)</div>   
              </div>    
              <div>                     
                <Button onClick={this.toggleManual} className={highlightAuto} >Auto</Button>
                <div className=''>Saves current data and automatically uses the latest data</div>  
              </div>            
            </FormGroup>
          </ModalBody>
          <ModalFooter className='dialog-footer'>
            <Button className='action-button button-blue' onClick={this.toggleModal}>Apply</Button>
          </ModalFooter>
        </Modal>
      </div>
    );
  }

}

UpdateFrequencySelect.propTypes = {
  lastUpdateCheck:  PropTypes.string.isRequired
};
