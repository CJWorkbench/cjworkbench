import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../components/Modal'
import memoize from 'memoize-one'
import { setDataVersionAction, setWfModuleNotificationsAction } from '../workflow-reducer'
import { connect } from 'react-redux'
import { createSelector } from 'reselect'
import { Trans } from '@lingui/macro'

const Months = [
  // AP style
  'Jan.',
  'Feb.',
  'March',
  'April',
  'May',
  'June',
  'July',
  'Aug.',
  'Sept.',
  'Oct.',
  'Nov.',
  'Dec.'
]

// Always print as if our time zone is UTC, when testing
// (all other solutions are worse, including env vars and pre-adjusted test data)
let _formatDateUTCforTesting = false
export function formatDateUTCForTesting () {
  _formatDateUTCforTesting = true
}

/**
 * Return AP-style date in the user's time zone, but with the date before the
 * time.
 *
 * For instance: "June 22, 2018 – 10:35 a.m."
 */
function formatDate (date) {
  let mon, dd, yyyy, hh, mm
  if (_formatDateUTCforTesting) {
    mon = Months[date.getUTCMonth()]
    dd = date.getUTCDate()
    yyyy = date.getUTCFullYear()
    hh = date.getUTCHours()
    mm = String(100 + date.getUTCMinutes()).slice(1) // 0-padded
  } else {
    mon = Months[date.getMonth()]
    dd = date.getDate()
    yyyy = date.getFullYear()
    hh = date.getHours()
    mm = String(100 + date.getMinutes()).slice(1) // 0-padded
  }
  let ampm = 'a.m.'

  if (hh === 0) {
    hh = 12
  } else if (hh === 12) {
    ampm = 'p.m.'
  } else if (hh > 12) {
    ampm = 'p.m.'
    hh -= 12
  }

  return `${mon} ${dd}, ${yyyy} – ${hh}:${mm} ${ampm}`
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
        <time time={date.toISOString()}>{formatDate(date)}</time>
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
              ? <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.status.alertsOn' description='The tag adds emphasis'>Alerts are <strong>on</strong></Trans>
              : <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.status.alertsOff' description='The tag adds emphasis'>Alerts are <strong>off</strong></Trans>
          }
          </p>
          <p className='description'>{
            checked
              ? <Trans id='js.WorkflowEditor.DataVersionModal.NotificationsForm.description.emailOnOutputChange'>You will receive and email if the output of this module changes</Trans>
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
    fetchWfModuleId: PropTypes.number.isRequired,
    fetchVersions: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      date: PropTypes.instanceOf(Date).isRequired,
      isSeen: PropTypes.bool.isRequired
    })).isRequired,
    selectedFetchVersionId: PropTypes.string, // null for no selection
    wfModuleId: PropTypes.number.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    notificationsEnabled: PropTypes.bool.isRequired, // whether enabled on selectedWfModule
    onClose: PropTypes.func.isRequired, // func() => undefined
    onChangeFetchVersionId: PropTypes.func.isRequired, // func(wfModuleId, versionId) => undefined
    onChangeNotificationsEnabled: PropTypes.func.isRequired // func(wfModuleId, isEnabled) => undefined
  }

  state = {
    selectedFetchVersionId: this.props.selectedFetchVersionId
  }

  handleChangeNotificationsEnabled = (isEnabled) => {
    const { onChangeNotificationsEnabled, wfModuleId } = this.props
    onChangeNotificationsEnabled(wfModuleId, isEnabled)
  }

  handleSelectSelectedFetchVersionId = (selectedFetchVersionId) => {
    this.setState({ selectedFetchVersionId })
  }

  handleSubmit = () => {
    if (this.state.selectedFetchVersionId !== this.props.selectedFetchVersionId) {
      const { fetchWfModuleId, onChangeFetchVersionId } = this.props
      onChangeFetchVersionId(fetchWfModuleId, this.state.selectedFetchVersionId)
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
        <ModalHeader toggle={onClose}>Data Versions</ModalHeader>
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
            >Load
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
const getWfModules = ({ wfModules }) => wfModules
const getSelectedTabWfModules = createSelector([getSelectedTab, getWfModules], (tab, wfModules) => {
  return tab.wf_module_ids.map(id => wfModules[String(id)] || null)
})
const getModules = ({ modules }) => modules
/**
 * Find first (WfModule, Module) that has a `.loads_data` ModuleVersion.
 */
const getFetchWfModule = createSelector([getSelectedTabWfModules, getModules], (wfModules, modules) => {
  for (const wfModule of wfModules) {
    const module = modules[wfModule.module] || {}
    if (module.loads_data) {
      return wfModule
    }
  }

  return null
})

/**
 * Parse `wfModule.versions.versions` Array of { id, date, isSeen }.
 *
 * wfModule.versions.versions is an Array of [ dateString, isSeen ]
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

function mapStateToProps (state, { wfModuleId }) {
  const fetchWfModule = getFetchWfModule(state)
  const wfModule = state.wfModules[String(wfModuleId)]
  const notificationsEnabled = wfModule ? wfModule.notifications : false

  return {
    fetchWfModuleId: fetchWfModule ? fetchWfModule.id : null,
    fetchVersions: fetchWfModule ? getFetchVersions(fetchWfModule.versions.versions || []) : null,
    selectedFetchVersionId: fetchWfModule ? fetchWfModule.versions.selected : null,
    isAnonymous: state.workflow.is_anonymous,
    notificationsEnabled
  }
}

const mapDispatchToProps = {
  onChangeFetchVersionId: setDataVersionAction,
  onChangeNotificationsEnabled: setWfModuleNotificationsAction
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(DataVersionModal)
