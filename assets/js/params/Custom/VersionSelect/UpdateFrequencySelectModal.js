import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../../components/Modal'

export default class UpdateFrequencySelectModal extends React.PureComponent {
  static propTypes = {
    isAutoUpdate: PropTypes.bool.isRequired,
    isEmailUpdates: PropTypes.bool.isRequired,
    timeNumber: PropTypes.number.isRequired,
    timeUnit: PropTypes.oneOf([ 'minutes', 'hours', 'days', 'weeks' ]).isRequired,
    onCancel: PropTypes.func.isRequired,
    onSubmit: PropTypes.func.isRequired,
  }

  state = {
    isAutoUpdate: this.props.isAutoUpdate,
    timeNumber: this.props.timeNumber,
    timeUnit: this.props.timeUnit
  }

  onChangeAutoUpdate = (ev) => {
    this.setState({
      isAutoUpdate: ev.target.value === 'true',
    })
  }

  onChangeEmailUpdates = (ev) => {
    this.props.setEmailUpdates(ev.target.checked)
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
    if (ev && ev.stopPropagation) ev.stopPropagation()

    const s = this.state
    const p = this.props

    if (
      s.isAutoUpdate === p.isAutoUpdate
      && s.timeUnit === p.timeUnit
      && s.timeNumber === p.timeNumber
    ) return this.props.onCancel()

    this.props.onSubmit({
      isAutoUpdate: s.isAutoUpdate,
      timeNumber: s.timeNumber,
      timeUnit: s.timeUnit,
    })
  }

  render() {
    const { isEmailUpdates } = this.props
    const { isAutoUpdate, timeNumber, timeUnit } = this.state

    return (
      <Modal isOpen={true} className='update-frequency-modal' toggle={this.props.onCancel}>
        <ModalHeader>WORKFLOW UPDATE</ModalHeader>
        <ModalBody>
          <form
            id='updateFrequencySelectModalForm'
            method='post'
            action='#'
            onReset={this.props.onCancel}
            onSubmit={this.onSubmit}
            >
            <div className={`big-radio big-radio-auto-update-true ${isAutoUpdate ? 'big-radio-checked' : 'big-radio-unchecked'}`}>
              <label>
                <input
                type='radio'
                name='isAutoUpdate'
                value='true'
                checked={isAutoUpdate}
                onChange={this.onChangeAutoUpdate}
                />
                <div className='radio'>Auto</div>
              </label>
              <div className='big-radio-details'>
                <p>Automatically update this workflow with the newest data (old versions will be saved).</p>
                <div className='form-group frequency'>
                  <label htmlFor='updateFrequencySelectTimeNumber'>Check for update every</label>
                  <div className='input-group'>
                    <div className='input-group-prepend'>
                      <input
                        className='form-control'
                        type='number'
                        name='timeNumber'
                        value={timeNumber}
                        onChange={this.onChangeTimeNumber}
                        disabled={!isAutoUpdate}
                        min='1'
                        max='60'
                        id='updateFrequencySelectTimeNumber'
                      />
                    </div>
                    <select
                      className='custom-select'
                      name='timeUnit'
                      value={timeUnit}
                      onChange={this.onChangeTimeUnit}
                      disabled={!isAutoUpdate}
                    >
                      <option value='minutes'>minutes</option>
                      <option value='hours'>hours</option>
                      <option value='days'>days</option>
                      <option value='weeks'>weeks</option>
                    </select>
                  </div>
                </div>
                <div className='form-check'>
                  <input
                    type='checkbox'
                    className='form-check-input'
                    id='update-frequency-select-modal-is-email-updates-checkbox'
                    name='isEmailUpdates'
                    checked={isEmailUpdates}
                    onChange={this.onChangeEmailUpdates}
                    disabled={!isAutoUpdate}
                  />
                  <label
                    className='form-check-label'
                    htmlFor='update-frequency-select-modal-is-email-updates-checkbox'
                  >
                    Email me when data changes
                  </label>
                </div>
              </div>
            </div>

            <div className={`big-radio big-radio-auto-update-false ${isAutoUpdate ? 'big-radio-unchecked' : 'big-radio-checked'}`}>
              <label>
                <input
                type='radio'
                name='isAutoUpdate'
                value='false'
                checked={!isAutoUpdate}
                onChange={this.onChangeAutoUpdate}
                />
                <div className='radio'>Manual</div>
              </label>
              <div className='big-radio-details'>
                <p>Check for new data manually.</p>
              </div>
            </div>
          </form>
        </ModalBody>
        <ModalFooter>
          <button type='reset' className='action-button button-gray' form='updateFrequencySelectModalForm'>Cancel</button>
          <button type='submit' className='action-button button-blue' form='updateFrequencySelectModalForm'>Apply</button>
        </ModalFooter>
      </Modal>
    )
  }
}
