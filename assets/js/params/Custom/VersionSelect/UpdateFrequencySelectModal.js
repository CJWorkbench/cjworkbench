import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../../components/Modal'
import { FormGroup, Label, Input } from '../../../components/Form'

export default class UpdateFrequencySelectModal extends React.PureComponent {
  constructor(props) {
    super(props)

    this.state = {
      isAutoUpdate: props.isAutoUpdate,
      isEmailUpdates: props.isEmailUpdates,
      timeNumber: props.timeNumber,
      timeUnit: props.timeUnit,
    }
  }

  onChangeAutoUpdate = (ev) => {
    this.setState({
      isAutoUpdate: ev.target.value === 'true',
    })
  }

  onChangeEmailUpdates = (ev) => {
    this.setState({
      isEmailUpdates: ev.target.checked,
    })
  }

  onChangeTimeNumber = (ev) => {
    this.setState({
      timeNumber: +ev.target.value || 0,
    })
  }

  onChangeTimeUnit = (ev) => {
    this.setState({
      timeUnit: ev.target.value,
    })
  }

  onSubmit = (ev) => {
    if (ev && ev.preventDefault) ev.preventDefault()

    const s = this.state
    const p = this.props

    if (
      s.isAutoUpdate === p.isAutoUpdate
      && s.timeUnit === p.timeUnit
      && s.timeNumber === p.timeNumber
      && s.isEmailUpdates === p.isEmailUpdates
    ) return this.props.onCancel()

    this.props.onSubmit({
      isAutoUpdate: s.isAutoUpdate,
      isEmailUpdates: s.isEmailUpdates,
      timeNumber: s.timeNumber,
      timeUnit: s.timeUnit,
    })
  }

  render() {
    const { isAutoUpdate, isEmailUpdates, timeNumber, timeUnit } = this.state

    return (

        <Modal isOpen={true}>
          <ModalHeader toggle={this.props.closeModal} className='dialog-header'>
            <span className="modal-title">WORKFLOW UPDATE</span>
          </ModalHeader>
          <ModalBody className="update-frequency-form">
            <form
              id="updateFrequencySelectModalForm"
              method="post"
              action="#"
              onCancel={this.props.onCancel}
              onSubmit={this.onSubmit}
              >
              <div className={`big-radio big-radio-auto-update-true ${isAutoUpdate ? 'big-radio-checked' : 'big-radio-unchecked'}`}>
                <label>
                  <input
                  type="radio"
                  name="isAutoUpdate"
                  value="true"
                  checked={isAutoUpdate}
                  onChange={this.onChangeAutoUpdate}
                  />
                  <div className="radio">Auto</div>
                </label>
                <div className="big-radio-details">
                  <p>Automatically update this workflow with the newest data (old versions will be saved).</p>
                  <Label className="details" for="updateFrequencySelectTimeNumber">Check for update every</Label>
                  <FormGroup className='update-freq-settings'>
                    <Input
                      type="number"
                      name="timeNumber"
                      value={timeNumber}
                      onChange={this.onChangeTimeNumber}
                      disabled={!isAutoUpdate}
                      min='1'
                      max='60'
                      id="updateFrequencySelectTimeNumber"
                      className='number-field t-d-gray content-2'>
                    </Input>
                    <Input
                      type="select"
                      name="timeUnit"
                      value={timeUnit}
                      onChange={this.onChangeTimeUnit}
                      disabled={!isAutoUpdate}
                      className='ml-3 input-dropdown'
                    >
                      <option value="minutes">minutes</option>
                      <option value="hours">hours</option>
                      <option value="days">days</option>
                      <option value="weeks">weeks</option>
                    </Input>
                  </FormGroup>
                  <FormGroup check>
                    <Label check>
                      <Input
                        type="checkbox"
                        name="isEmailUpdates"
                        checked={isEmailUpdates}
                        onChange={this.onChangeEmailUpdates}
                        disabled={!isAutoUpdate}
                        />{' '}
                      Email me when data changes
                    </Label>
                  </FormGroup>
                </div>
              </div>

              <div className={`big-radio big-radio-auto-update-false ${isAutoUpdate ? 'big-radio-unchecked' : 'big-radio-checked'}`}>
                <label>
                  <input
                  type="radio"
                  name="isAutoUpdate"
                  value="false"
                  checked={!isAutoUpdate}
                  onChange={this.onChangeAutoUpdate}
                  />
                  <div className="radio">Manual</div>
                </label>
                <div className="big-radio-details">
                  <p>Check for new data manually.</p>
                </div>
              </div>
            </form>
          </ModalBody>
          <ModalFooter>
            <button type='button' type="cancel" className="action-button button-gray" form="updateFrequencySelectModalForm">Cancel</button>
            <button type='button' type="submit" className="action-button button-blue" form="updateFrequencySelectModalForm">Apply</button>
          </ModalFooter>
        </Modal>

    )
  }
}

UpdateFrequencySelectModal.propTypes = {
  isAutoUpdate: PropTypes.bool.isRequired,
  isEmailUpdates: PropTypes.bool.isRequired,
  timeNumber: PropTypes.number.isRequired,
  timeUnit: PropTypes.oneOf([ 'minutes', 'hours', 'days', 'weeks' ]).isRequired,
  onCancel: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
}
