import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import { Form, FormGroup, Label, Input } from 'reactstrap'
import { timeDifference } from '../utils'
import { store, updateWfModuleAction } from '../workflow-reducer'

export default class UpdateFrequencySelect extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      modalOpen: false,
      message: "",
      liveSettings: {
        manual: !this.props.updateSettings.autoUpdateData,
        period: this.props.updateSettings.updateInterval,
        unit: this.props.updateSettings.updateUnits
      }
    };
    this.state.dialogSettings = Object.assign({}, this.state.liveSettings);

    // Allow props to specify a conversion from browser time to displayed time, so tests can run in UTC (not test machine tz)
    if (props.timezoneOffset != undefined) {
      this.state.timezoneOffset = props.timezoneOffset;
    } else {
      this.state.timezoneOffset = 0; // display in browser local time
    }

    this.toggleModal = this.toggleModal.bind(this);
    this.toggleManual = this.toggleManual.bind(this);
    this.updatePeriod = this.updatePeriod.bind(this);
    this.updateUnit = this.updateUnit.bind(this);
    this.saveSettings = this.saveSettings.bind(this);
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.notifications && (!this.props.notifications && this.state.liveSettings.manual)) {
      this.toggleModal();
      this.toggleManual();
      this.setState({
        message: "Choose a frequency to check on new data and click 'Apply'."
      })
    }
  }

  toggleModal() {
    if (!this.props.isReadOnly) {
      this.setState({
        modalOpen: !this.state.modalOpen,
        dialogSettings: Object.assign({}, this.state.liveSettings)
      }, () => {
        if (!this.state.modalOpen && this.state.liveSettings.manual && this.props.notifications) {
          store.dispatch(updateWfModuleAction(this.props.wfModuleId, {
            notifications: false
          }));
        }
      });
    }
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
    this.props.api.setWfModuleUpdateSettings(this.props.wfModuleId, params);
    this.setState({liveSettings: Object.assign({}, this.state.dialogSettings)}, () => {
      this.toggleModal();
    });
  }


  render() {

    // button highlights
    var highlightManual = 'action-button manual-button ' + (this.state.dialogSettings.manual ? 'button-blue--fill' : 'button-gray ');
    var highlightAuto = 'action-button auto-button ' + (!this.state.dialogSettings.manual ? 'button-blue--fill' : 'button-gray');

    // info shown on Wf Module card
    var manual = this.state.liveSettings.manual;
    var period = this.state.liveSettings.period;
    var unit = this.state.liveSettings.unit;
    var settingsInfo = manual ? 'manual' :'auto'

    var lastChecked = null;
    var now = new Date();
    if (this.props.updateSettings.lastUpdateCheck)
      lastChecked = <div className='content-4 t-m-gray'>
                      Checked {timeDifference(this.props.updateSettings.lastUpdateCheck, now)}
                    </div>

    return (
      <div className='frequency-item'>
        <div>
          <span className='content-3 t-d-gray'>Update </span>
          <span className='content-3 ml-1 t-f-blue test-modal-button' onClick={this.toggleModal}>{settingsInfo}</span>
        </div>
        {lastChecked}
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className='modal-dialog'>
          <ModalHeader toggle={this.toggleModal} className='dialog-header'>
            <span className='title-4 t-d-gray'>SYNC SETTINGS</span>
          </ModalHeader>
          <ModalBody className='dialog-body'>
            {this.state.message.length > 0 &&
              <div className='info-3 mt-2 mb-5'>{this.state.message}</div>
            }
            <FormGroup>
              <div className="row">
                <div className="col-sm-3">
                  <div onClick={this.toggleManual} className={highlightAuto}>On</div>
                </div>

                <div className="col-sm-9">
                  <div className='info-2'>Automatically save the current version of the workflow and update it with the newest data.</div>
                  <Label for="updateFreq" className='content-3 t-d-gray mt-4 mb-2'>Check for update every</Label>
                  <div className='update-freq-settings update-freq-test-class mb-5'>
                    <Input
                      type="number"
                      onChange={this.updatePeriod}
                      value={this.state.dialogSettings.period}
                      min='1'
                      max='500'
                      name="updateFreq"
                      id="updateFreqNum"
                      className='number-field t-d-gray content-2'>
                    </Input>
                    <Input
                      type="select"
                      value={this.state.dialogSettings.unit}
                      onChange={this.updateUnit}
                      name="updateFreq"
                      id="updateFreqUnit"
                      className='ml-3 input-dropdown'
                    >
                      <option>minutes</option>
                      <option>hours</option>
                      <option id='days-option'>days</option>
                      <option>weeks</option>
                    </Input>
                  </div>
                </div>
              </div>

              <div className="row d-flex align-items-center">
                <div className="col-sm-3">
                  <div onClick={this.toggleManual} className={highlightManual}>Off</div>
                </div>

                <div className="col-sm-9">
                  <div className='info-2'>Check for new data manually.</div>
                </div>
              </div>
            </FormGroup>
          </ModalBody>
          <ModalFooter className='dialog-footer'>
            <div className='action-button button-gray test-cancel-button mr-4' onClick={this.toggleModal}>Cancel</div>
            <div className='action-button button-blue test-ok-button' onClick={this.saveSettings}>Apply</div>

          </ModalFooter>
        </Modal>
      </div>
    );
  }

}

UpdateFrequencySelect.propTypes = {
  api:              PropTypes.object.isRequired,
  updateSettings:   PropTypes.object.isRequired,
  wfModuleId:       PropTypes.number.isRequired
};
