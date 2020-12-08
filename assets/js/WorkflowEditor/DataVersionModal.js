import React from 'react'
import { i18n } from '@lingui/core'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../components/Modal'
import memoize from 'memoize-one'
import { setDataVersionAction, setStepNotificationsAction } from '../workflow-reducer'
import { connect } from 'react-redux'
import { createSelector } from 'reselect'
import { Trans } from '@lingui/macro'

// Always print as if our time zone is UTC, when testing
// (all other solutions are worse, including env vars and pre-adjusted test data)
let _formatDateUTCforTesting = false
export function formatDateUTCForTesting () {
  _formatDateUTCforTesting = true
}

/**
 * Form <input type="radio">. Calls onSelect on change.
 */
class FetchVersion extends React.PureComponent {
  static propTypes = {
    id: PropTypes.string.isRequired, // version ID
    date: PropTypes.instanceOf(Date).isRequired, // version date
    isSelected: PropTypes.bool.isRequired,
    isSeen: PropTypes.bool.isRequired, // has user selected this version ever
    onSelect: PropTypes.func.isRequired // func(versionId) => undefined
  }

  handleChange = (ev) => {
    if (ev.target.checked) {
      this.props.onSelect(this.props.id)
    }
  }

  render () {
    const { id, date, isSeen, isSelected } = this.props

    let className = isSeen ? 'seen' : 'unseen'
    if (isSelected) className += ' selected'

    return (
      <label className={className}>
        <input type='radio' name='data-version' value={id} checked={isSelected} onChange={this.handleChange} />
        <time time={date.toISOString()}>
          {i18n.date(date, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: 'numeric',
            hour12: true,
            timeZone: _formatDateUTCforTesting ? 'UTC' : undefined
          })}
        </time>
      </label>
    )
  }
}

/**
 * Form that calls onSubmit(wantNotifications).
 *
 * Implemented as a checkbox with an onChange event. ([2018-06-22] it _looks_
 * like a <button>, but it's a checkbox in a <label>.)
 */
class NotificationsForm extends React.PureComponent {
  static propTypes = {
    notificationsEnabled: PropTypes.bool.isRequired,
    onSubmit: PropTypes.func.isRequired // func(bool) => undefined
  }

  handleChange = (ev) => {
    this.props.onSubmit(ev.target.checked) // should change the state
  }

  handleSubmit = (ev) => {
    ev.preventDefault()
    ev.stopPropagation()
  }

  render () {
    const checked = this.props.notificationsEnabled
    const className = checked ? 'notifications-enabled' : 'notifications-disabled'
    const iconAlert = checked ? 'icon-notification' : 'icon-no-notification'

    return (
      <form onSubmit={this.handleSubmit} className={`notifications ${className}`}>
        <div className='text'>
          <p className='status'><i className={`icon ${iconAlert}`} />{
            checked
              ? <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.status.alertsOn' comment='The tag adds emphasis'>Alerts are <strong>on</strong></Trans>
              : <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.status.alertsOff' comment='The tag adds emphasis'>Alerts are <strong>off</strong></Trans>
          }
          </p>
          <p className='description'>{
            checked
              ? <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.description.emailOnOutputChange'>You will receive an email if the output of this module changes</Trans>
              : <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.description.turnAlertsOn'>Turn alerts ON to receive an email if the output of this module changes</Trans>
          }
          </p>
        </div>
        <div className='options'>
          <label>
            <input name='notifications-enabled' type='checkbox' checked={checked} onChange={this.handleChange} />
            <span className='action'>{checked ? <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.options.turnOff'>Turn off</Trans> : <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.options.turnOn'>Turn on</Trans>}</span>
          </label>
        </div>
      </form>
    )
  }
}

export class DataVersionModal extends React.PureComponent {
  static propTypes = {
    fetchStepId: PropTypes.number.isRequired,
    fetchVersions: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      date: PropTypes.instanceOf(Date).isRequired,
      isSeen: PropTypes.bool.isRequired
    })).isRequired,
    selectedFetchVersionId: PropTypes.string, // null for no selection
    stepId: PropTypes.number.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    notificationsEnabled: PropTypes.bool.isRequired, // whether enabled on selectedStep
    onClose: PropTypes.func.isRequired, // func() => undefined
    onChangeFetchVersionId: PropTypes.func.isRequired, // func(stepId, versionId) => undefined
    onChangeNotificationsEnabled: PropTypes.func.isRequired // func(stepId, isEnabled) => undefined
  }

  state = {
    selectedFetchVersionId: this.props.selectedFetchVersionId
  }

  handleChangeNotificationsEnabled = (isEnabled) => {
    const { onChangeNotificationsEnabled, stepId } = this.props
    onChangeNotificationsEnabled(stepId, isEnabled)
  }

  handleSelectSelectedFetchVersionId = (selectedFetchVersionId) => {
    this.setState({ selectedFetchVersionId })
  }

  handleSubmit = () => {
    if (this.state.selectedFetchVersionId !== this.props.selectedFetchVersionId) {
      const { fetchStepId, onChangeFetchVersionId } = this.props
      onChangeFetchVersionId(fetchStepId, this.state.selectedFetchVersionId)
    }

    this.props.onClose()
  }

  render () {
    const {
      fetchVersions,
      onClose,
      isAnonymous,
      notificationsEnabled
    } = this.props

    return (
      <Modal className='data-versions-modal' isOpen fade={false} toggle={onClose}>
        <ModalHeader toggle={onClose}>
          <Trans id='js.WorkflowEditor.DataVersionModal.ModalHeader'>Data Versions</Trans>
        </ModalHeader>
        <ModalBody>
          <form onSubmit={this.handleSubmit} onCancel={onClose}>
            <ol>
              {fetchVersions.map(v => (
                <li key={v.id}>
                  <FetchVersion
                    onSelect={this.handleSelectSelectedFetchVersionId}
                    isSelected={this.state.selectedFetchVersionId === v.id}
                    {...v}
                  />
                </li>
              ))}
            </ol>
          </form>
        </ModalBody>
        <ModalFooter>
          {isAnonymous ? null : (
            <NotificationsForm
              notificationsEnabled={notificationsEnabled}
              onSubmit={this.handleChangeNotificationsEnabled}
            />
          )}
          <div className='actions'>
            <button
              name='load'
              disabled={this.state.selectedFetchVersionId === this.props.selectedFetchVersionId}
              onClick={this.handleSubmit}
            >
              <Trans id='js.WorkflowEditor.DataVersionModal.ModalFooter.actions.loadButton'>Load</Trans>
            </button>
          </div>
        </ModalFooter>
      </Modal>
    )
  }
}

const getWorkflow = ({ workflow }) => workflow
const getTabs = ({ tabs }) => tabs
const getSelectedTab = createSelector([getWorkflow, getTabs], (workflow, tabs) => {
  return tabs[workflow.tab_slugs[workflow.selected_tab_position]]
})
const getSteps = ({ steps }) => steps
const getSelectedTabSteps = createSelector([getSelectedTab, getSteps], (tab, steps) => {
  return tab.step_ids.map(id => steps[String(id)] || null)
})
const getModules = ({ modules }) => modules
/**
 * Find first (Step, Module) that has a `.loads_data` ModuleVersion.
 */
const getFetchStep = createSelector([getSelectedTabSteps, getModules], (steps, modules) => {
  for (const step of steps) {
    const module = modules[step.module] || {}
    if (module.loads_data) {
      return step
    }
  }

  return null
})

/**
 * Parse `step.versions.versions` Array of { id, date, isSeen }.
 *
 * step.versions.versions is an Array of [ dateString, isSeen ]
 * pairs.
 */
const getFetchVersions = memoize(versions => {
  return versions.map(version => {
    const [id, isSeen] = version
    return {
      id,
      isSeen,
      date: new Date(id)
    }
  })
})

function mapStateToProps (state, { stepId }) {
  const fetchStep = getFetchStep(state)
  const step = state.steps[String(stepId)]
  const notificationsEnabled = step ? step.notifications : false

  return {
    fetchStepId: fetchStep ? fetchStep.id : null,
    fetchVersions: fetchStep ? getFetchVersions(fetchStep.versions.versions || []) : null,
    selectedFetchVersionId: fetchStep ? fetchStep.versions.selected : null,
    isAnonymous: state.workflow.is_anonymous,
    notificationsEnabled
  }
}

const mapDispatchToProps = {
  onChangeFetchVersionId: setDataVersionAction,
  onChangeNotificationsEnabled: setStepNotificationsAction
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(DataVersionModal)
