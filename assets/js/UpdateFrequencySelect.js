import React from 'react'
import PropTypes from 'prop-types'
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import { Form, FormGroup, Label, Input } from 'reactstrap'
import workbenchapi from './WorkbenchAPI';
import dateFormat from 'dateformat'


export default class UpdateFrequencySelect extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      modalOpen: false,
      liveSettings: {
        manual: !this.props.updateSettings.autoUpdateData,
        period: this.props.updateSettings.updateInterval,
        unit: this.props.updateSettings.updateUnits
      },
      dialogSettings: {
        manual: !this.props.updateSettings.autoUpdateData,
        period: this.props.updateSettings.updateInterval,
        unit: this.props.updateSettings.updateUnits
      }
    };

    // Allow props to specify a conversion from browser time to displayed time, so tests can run in UTC (not test machine tz) 
    if (props.timezoneOffset != undefined) {
      this.state.timezoneOffset = props.timezoneOffset;
    } else {
      this.state.timezoneOffset = 0; // display in browser local time 
    }

    this.api = workbenchapi();
    this.toggleModal = this.toggleModal.bind(this);
    this.toggleManual = this.toggleManual.bind(this);  
    this.updatePeriod = this.updatePeriod.bind(this);    
    this.updateUnit = this.updateUnit.bind(this);   
    this.saveSettings = this.saveSettings.bind(this);    
  }

  toggleModal() {
    this.setState({modalOpen: !this.state.modalOpen })
  }

  toggleManual() {
    this.setState(
      {dialogSettings: { 
        manual: !this.state.dialogSettings.manual,
        period: this.state.dialogSettings.period,
        unit: this.state.dialogSettings.unit
    }});
  }

  updatePeriod(event) {
    this.setState(
        {dialogSettings: { 
          manual: this.state.dialogSettings.manual,
          period: event.target.value,
          unit: this.state.dialogSettings.unit
    }});
  }

  updateUnit(event) {
    this.setState(
      {dialogSettings: { 
        manual: this.state.dialogSettings.manual,
        period: this.state.dialogSettings.period,
        unit: event.target.value
    }});
  }

  saveSettings() {
    var params = {
      auto_update_data: !this.state.dialogSettings.manual,
      update_interval: this.state.dialogSettings.period,
      update_units: this.state.dialogSettings.unit
    };
    this.api.setWfModuleUpdateSettings(this.props.wfModuleId, params); 
    this.setState({liveSettings: this.state.dialogSettings});
    this.toggleModal();
  }

  render() {

    //button highlights
    var highlightManual = this.state.dialogSettings.manual ? 'action-button button-full-blue' : 'action-button button-gray';
    var highlightAuto = !this.state.dialogSettings.manual ? 'action-button button-full-blue' : 'action-button button-gray';

    var manualText = this.state.dialogSettings.manual ? 'action-button button-full-blue' : 'action-button button-gray';
    var autoText = !this.state.dialogSettings.manual ? 'action-button button-full-blue' : 'action-button button-gray';
    

    // info shown on Wf Module card
    var manual = this.state.liveSettings.manual;
    var period = this.state.liveSettings.period;
    var unit = this.state.liveSettings.unit;
    var settingsInfo = manual 
      ? 'Manual'
      :'Auto, every ' + period + ' ' + unit;

    var lastChecked = null;
    if (this.props.updateSettings.lastUpdateCheck) 
      lastChecked = <div className='content-3 t-m-gray'>Last checked: {dateFormat(this.props.updateSettings.lastUpdateCheck, "mmmm d yyyy - hh:MM TT")}</div>
      
    return (
      <div className='version-item'>
        <div className='' >
          <span className='content-3 t-d-gray'>Update: </span>
          <span className='content-3 t-f-blue' onClick={this.toggleModal}>{settingsInfo}</span>  
        </div>
        {lastChecked}
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className='dialog-window'>
          <ModalHeader toggle={this.toggleModal} className='dialog-header'>
            <span className='title-4 t-d-gray'>Sync Settings</span>
          </ModalHeader>
          <ModalBody className='dialog-body'>
            <FormGroup>
              <Label for="updateFreq" className='content-3 t-d-gray mb-2'>Check for update every</Label>
              <div className='update-freq-settings update-freq-test-class mb-2'>
                <Input 
                  type="number" 
                  onChange={this.updatePeriod}
                  value={this.state.dialogSettings.period}
                  min='1' 
                  max='500' 
                  name="updateFreq" 
                  id="updateFreqNum">
                </Input>
                <Input 
                  type="select" 
                  value={this.state.dialogSettings.unit}
                  onChange={this.updateUnit}
                  name="updateFreq" 
                  id="updateFreqPeriod" 
                >
                  <option>seconds</option>
                  <option>minutes</option>
                  <option>hours</option>                
                  <option>days</option>
                  <option>weeks</option>
                </Input>
              </div>
              <div className='content-3 t-d-gray mb-2'>When an update is found:</div>
              <div className="d-flex flex-row mb-2">
                <div onClick={this.toggleManual} className={highlightManual} >Manual</div>
                <div className='t-d-gray info-1'>Notify me, but do not update the workflow. (recommended)</div>   
              </div>    
              <div className="d-flex flex-row mb-2">                     
                <div onClick={this.toggleManual} className={highlightAuto} >Auto</div>
                <div className='t-d-gray info-1'>Automatically save the current version of the workflow and update it with the newest data.</div>  
              </div>            
            </FormGroup>
          </ModalBody>
          <ModalFooter className='dialog-footer'>
            <div className='action-button button-blue' onClick={this.saveSettings}>OK</div>
            <div className='action-button button-blue' onClick={this.toggleModal}>Cancel</div>            
          </ModalFooter>
        </Modal>
      </div>
    );
  }

}

UpdateFrequencySelect.propTypes = {
  updateSettings:   PropTypes.object.isRequired,
  wfModuleId:       PropTypes.number.isRequired
};
