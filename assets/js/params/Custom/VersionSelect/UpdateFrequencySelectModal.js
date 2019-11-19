import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../../components/Modal'
import QuotaExceeded from './QuotaExceeded'
import { withI18n } from '@lingui/react'
import { Trans, t } from '@lingui/macro'

const TimeUnits = {
  seconds: 1,
  minutes: 60,
  hours: 3600,
  days: 86400,
  weeks: 604800
}

function findBestTimeUnitForNSeconds (nSeconds) {
  for (const timeUnit of ['weeks', 'days', 'hours', 'minutes']) {
    if (nSeconds % TimeUnits[timeUnit] === 0) {
      return timeUnit
    }
  }
  return 'seconds'
}

function calculateFetchInterval ({ wantTimeUnitCount, timeUnit }) {
  const value = parseFloat(wantTimeUnitCount) // may be NaN
  if (value > 0) {
    return Math.max(1, TimeUnits[timeUnit] * value)
  } else {
    return null
  }
}

class UpdateFrequencySelectModal extends React.PureComponent {
  static propTypes = {
    workflowId: PropTypes.number.isRequired,
    wfModuleId: PropTypes.number.isRequired,
    isAutofetch: PropTypes.bool.isRequired,
    fetchInterval: PropTypes.number.isRequired,
    isEmailUpdates: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired, // func() => undefined
    setEmailUpdates: PropTypes.func.isRequired, // func(isEmailUpdates) => undefined
    trySetAutofetch: PropTypes.func.isRequired, // func(isAutofetch, fetchInterval) => Promise[Optional[quotaExceeded]]
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    })
  }

  state = {
    isSettingAutofetch: false, // true means ignore quotaExceeded because we are going to change it
    quotaExceeded: null, // JSON response piece -- set iff we exceeded quota
    // "want" is what we show in the UI. The server can say no to autofetch
    // requests; if it does, we need to keep a handle on what the user wanted.
    // (Otherwise the user's input would disappear upon server response.)
    wantAutofetch: this.props.isAutofetch,
    timeUnit: findBestTimeUnitForNSeconds(this.props.fetchInterval),
    // wantTimeUnitCount is string is so the user can type "1.5" ... or erase
    // the value and type something new. this.wantFetchInterval is null when
    // the user enters an invalid wantTimeUnitCount.
    wantTimeUnitCount: String(this.props.fetchInterval / TimeUnits[findBestTimeUnitForNSeconds(this.props.fetchInterval)])
  }

  get wantFetchInterval () {
    return calculateFetchInterval(this.state)
  }

  get isFetchIntervalSubmittable () {
    return (
      !this.state.isSettingAutofetch && // there's no pending request
      this.wantFetchInterval && // the text box is valid
      (
        // we've edited
        this.wantFetchInterval !== this.props.fetchInterval ||
        this.wantAutofetch !== this.props.isAutofetch
      )
    )
  }

  handleChangeAutofetch = (ev) => {
    this.setState({
      wantAutofetch: ev.target.value === 'true'
    }, this.handleSubmit)
  }

  handleChangeEmailUpdates = (ev) => {
    this.props.setEmailUpdates(ev.target.checked)
  }

  handleChangeTimeUnitCount = (ev) => {
    this.setState({ wantTimeUnitCount: ev.target.value })
  }

  handleChangeTimeUnit = (ev) => {
    this.setState({
      timeUnit: ev.target.value
    })
  }

  handleSubmit = (ev) => {
    if (ev && ev.preventDefault) ev.preventDefault()
    if (ev && ev.stopPropagation) ev.stopPropagation()

    this.setState((state, props) => {
      const { isSettingAutofetch, isAutofetch, fetchInterval, trySetAutofetch } = props
      const { wantAutofetch } = state
      const wantFetchInterval = calculateFetchInterval(state) || fetchInterval

      if (isSettingAutofetch) return // only one submit at a time, please
      if (wantAutofetch === isAutofetch && wantFetchInterval === fetchInterval) return // state == props

      // "Lock" state against future submits (isSettingAutofetch); then submit
      // and handle the response asynchronously.
      trySetAutofetch(wantAutofetch, wantFetchInterval)
        .then(({ value: { quotaExceeded, fetchInterval } }) => {
          this.setState(state => {
            const nextState = {
              isSettingAutofetch: false,
              quotaExceeded: quotaExceeded || null
            }
            if (!quotaExceeded) {
              // If user asked for "5"s, replace with server-supplied "300"s.
              nextState.wantTimeUnitCount = String(fetchInterval / TimeUnits[state.timeUnit])
            }
            return nextState
          })
        })

      return { isSettingAutofetch: true }
    })
  }

  render () {
    const { isEmailUpdates, onClose, workflowId, wfModuleId, i18n } = this.props
    const { wantAutofetch, wantTimeUnitCount, isSettingAutofetch, quotaExceeded, timeUnit } = this.state

    return (
      <Modal isOpen className='update-frequency-modal' toggle={onClose}>
        <ModalHeader>
          <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.header.title' description='This should be all-caps for styling reasons'>WORKFLOW UPDATE</Trans>
        </ModalHeader>
        <ModalBody>
          <form
            className='autofetch'
            method='post'
            action='#'
            onSubmit={this.handleSubmit}
          >
            {/* disable fieldset if we're submitting -- the user can't submit during apply, and the user shouldn't be allowed to edit fields because that would be confusing. */}
            <fieldset className='autofetch' disabled={isSettingAutofetch}>
              <div className={`big-radio big-radio-auto-update-true ${wantAutofetch ? 'big-radio-checked' : 'big-radio-unchecked'}`}>
                <label>
                  <input
                    type='radio'
                    name='isAutofetch'
                    value='true'
                    checked={wantAutofetch}
                    onChange={this.handleChangeAutofetch}
                  />
                  <div className='radio'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.auto.label'>Auto</Trans></div>
                </label>
                <div className='big-radio-details'>
                  <p><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.auto.description'>Automatically update this workflow with the newest data (old versions will be saved).</Trans></p>
                  <label htmlFor='updateFrequencySelectTimeUnitCount'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.label'>Check for update every</Trans></label>
                  <fieldset className='fetch-interval' disabled={!wantAutofetch}>
                    <div className='input-group'>
                      <div className='input-group-prepend'>
                        <input
                          className='form-control'
                          type='number'
                          name='timeUnitCount'
                          value={wantTimeUnitCount}
                          onChange={this.handleChangeTimeUnitCount}
                          min='1'
                          id='updateFrequencySelectTimeUnitCount'
                        />
                      </div>
                      <select
                        className='custom-select'
                        name='timeUnit'
                        value={timeUnit}
                        onChange={this.handleChangeTimeUnit}
                      >
                        <option value='weeks'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.weeks.option'>weeks</Trans></option>
                        <option value='days'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.days.option'>days</Trans></option>
                        <option value='hours'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.hours.option'>hours</Trans></option>
                        <option value='minutes'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.minutes.option'>minutes</Trans></option>
                        <option value='seconds'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.seconds.option'>seconds</Trans></option>
                      </select>
                      <div className='input-group-append'>
                        <button
                          className='form-control'
                          type='submit'
                          name='apply'
                          disabled={!this.isFetchIntervalSubmittable}
                        >
                          {quotaExceeded ? <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.retry'>Retry</Trans> : <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.apply'>Apply</Trans>}
                        </button>
                      </div>
                    </div>{/* input-group */}
                  </fieldset>
                </div>{/* big-radio-details */}
              </div>{/* big-radio */}

              {quotaExceeded ? (
                <QuotaExceeded
                  workflowId={workflowId}
                  wfModuleId={wfModuleId}
                  {...quotaExceeded}
                />
              ) : null}

              <div className={`big-radio big-radio-auto-update-false ${wantAutofetch ? 'big-radio-unchecked' : 'big-radio-checked'}`}>
                <label>
                  <input
                    type='radio'
                    name='isAutofetch'
                    value='false'
                    checked={!wantAutofetch}
                    onChange={this.handleChangeAutofetch}
                  />
                  <div className='radio'><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.manual.label'>Manual</Trans></div>
                </label>
                <div className='big-radio-details'>
                  <p><Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.manual.description'>Check for new data manually.</Trans></p>
                </div>
              </div>
            </fieldset>
          </form>

          <div className='email-updates'>
            <input
              type='checkbox'
              id='update-frequency-select-modal-is-email-updates-checkbox'
              name='isEmailUpdates'
              checked={isEmailUpdates}
              onChange={this.handleChangeEmailUpdates}
            />
            <label
              htmlFor='update-frequency-select-modal-is-email-updates-checkbox'
            >
              <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.emailUpdates.label'>Email me when data changes</Trans>
            </label>
          </div>
        </ModalBody>
        <ModalFooter>
          <button type='button' className='close' title={i18n._(t('js.params.Custom.VersionSelect.UpdateFrequencySelectModal.footer.close.placeholder')`Close`)} onClick={onClose}>
            <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.footer.closeButton'>Close</Trans>
          </button>
        </ModalFooter>
      </Modal>
    )
  }
}

export default withI18n()(UpdateFrequencySelectModal)
