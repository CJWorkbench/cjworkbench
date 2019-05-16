import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../components/Modal'
import memoize from 'memoize-one'
import { setDataVersionAction, updateWfModuleAction } from '../workflow-reducer'
import { connect } from 'react-redux'
import { createSelector } from 'reselect'

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
  'Dec.',
]

// Always print as if our time zone is UTC, when testing
// (all other solutions are worse, including env vars and pre-adjusted test data)
let _formatDateUTCforTesting = false
export function formatDateUTCForTesting() {
  _formatDateUTCforTesting = true
}

/**
 * Return AP-style date in the user's time zone, but with the date before the
 * time.
 *
 * For instance: "June 22, 2018 – 10:35 a.m."
 */
function formatDate(date) {
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
    onSelect: PropTypes.func.isRequired, // func(versionId) => undefined
  }

  onChange = (ev) => {
    if (ev.target.checked) {
      this.props.onSelect(this.props.id)
    }
  }

  render() {
    const { id, date, isSeen, isSelected } = this.props

    let className = isSeen ? 'seen' : 'unseen'
    if (isSelected) className += ' selected'

    return (
      <label className={className}>
        <input type="radio" name="data-version" value={id} checked={isSelected} onChange={this.onChange} />
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
    onSubmit: PropTypes.func.isRequired, // func(bool) => undefined
  }

  onChange = (ev) => {
    this.props.onSubmit(ev.target.checked) // should change the state
  }

  render() {
    const checked = this.props.notificationsEnabled

    const className = checked ? 'notifications-enabled' : 'notifications-disabled'

    const iconAlert = checked ? 'icon-notification' : 'icon-no-notification'

    return (
      <form onSubmit={this.onSubmit} className={`notifications ${className}`}>
        <div className="text">
          <p className="status"><i className={`icon ${iconAlert}`}/> Alerts are <strong>{checked ? ' on' : ' off'}</strong></p>
          <p className="description">{ checked ? (
            'You will receive and email if the output of this module changes'
          ) : (
            'Turn alerts ON to receive an email if the output of this module changes'
          )}</p>
        </div>
        <div className="options">
          <label>
            <input name="notifications-enabled" type="checkbox" checked={checked} onChange={this.onChange}/>
            <span className="action">{checked ? 'Turn off' : 'Turn on'}</span>
          </label>
        </div>
      </form>
    )
  }
}

export class DataVersionModal extends React.PureComponent {
  static propTypes = {
    fetchWfModuleId: PropTypes.number.isRequired,
    fetchWfModuleName: PropTypes.string.isRequired,
    fetchVersions: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      date: PropTypes.instanceOf(Date).isRequired,
      isSeen: PropTypes.bool.isRequired,
    })).isRequired,
    selectedFetchVersionId: PropTypes.string, // null for no selection
    wfModuleId: PropTypes.number.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    notificationsEnabled: PropTypes.bool.isRequired, // whether enabled on selectedWfModule
    onClose: PropTypes.func.isRequired, // func() => undefined
    onChangeFetchVersionId: PropTypes.func.isRequired, // func(wfModuleId, versionId) => undefined
    onChangeNotificationsEnabled: PropTypes.func.isRequired, // func(wfModuleId, isEnabled) => undefined
  }

  state = {
    selectedFetchVersionId: this.props.selectedFetchVersionId
  }

  onChangeNotificationsEnabled = (isEnabled) => {
    const { onChangeNotificationsEnabled, wfModuleId } = this.props
    onChangeNotificationsEnabled(wfModuleId, isEnabled)
  }

  setSelectedFetchVersionId = (selectedFetchVersionId) => {
    this.setState({ selectedFetchVersionId })
  }

  onSubmit = () => {
    if (this.state.selectedFetchVersionId !== this.props.selectedFetchVersionId) {
      const { fetchWfModuleId, onChangeFetchVersionId } = this.props
      onChangeFetchVersionId(fetchWfModuleId, this.state.selectedFetchVersionId)
    }

    this.props.onClose()
  }

  render() {
    const {
      fetchWfModuleName,
      fetchVersions,
      onClose,
      isAnonymous,
      notificationsEnabled,
    } = this.props

    return (
      <Modal className="data-versions-modal" isOpen={true} fade={false} toggle={onClose}>
        <ModalHeader toggle={onClose}>Data Versions</ModalHeader>
        <ModalBody>
          <form onSubmit={this.onSubmit} onCancel={this.onClose}>
            {/* <p className="introduction">These are the versions of “{fetchWfModuleName}” that we have stored:</p> */}
            <ol>
              {fetchVersions.map(v => <li key={v.id}><FetchVersion
                onSelect={this.setSelectedFetchVersionId}
                isSelected={this.state.selectedFetchVersionId === v.id}
                {...v}
                /></li>)}
            </ol>
          </form>
        </ModalBody>
        <ModalFooter>
          { isAnonymous ? null : (
            <NotificationsForm
              notificationsEnabled={notificationsEnabled}
              onSubmit={this.onChangeNotificationsEnabled}
              />
          )}
          <div className="actions">
            <button
              name="load"
              disabled={this.state.selectedFetchVersionId === this.props.selectedFetchVersionId}
              onClick={this.onSubmit}
              >Load</button>
          </div>
        </ModalFooter>
      </Modal>
    )
  }
}

const getWorkflow = ({ workflow }) => workflow
const getTabs = ({ tabs }) => tabs
const getSelectedTab = createSelector([ getWorkflow, getTabs ], (workflow, tabs) => {
  return tabs[workflow.tab_slugs[workflow.selected_tab_position]]
})
const getWfModules = ({ wfModules }) => wfModules
const getSelectedTabWfModules = createSelector([ getSelectedTab, getWfModules ], (tab, wfModules) => {
  return tab.wf_module_ids.map(id => wfModules[String(id)] || null)
})
const getModules = ({ modules }) => modules
/**
 * Find first (WfModule, Module) that has a `.loads_data` ModuleVersion.
 */
const getFetchWfModule = createSelector([ getSelectedTabWfModules, getModules ], (wfModules, modules) => {
  for (const wfModule of wfModules) {
    const module = modules[wfModule.module] || {}
    if (module.loads_data) {
      return { fetchWfModule: wfModule, fetchModule: module }
    }
  }

  return { fetchWfModule: null, fetchModule: null }
})

/**
 * Parse `wfModule.versions.versions` Array of { id, date, isSeen }.
 *
 * wfModule.versions.versions is an Array of [ dateString, isSeen ]
 * pairs.
 */
const getFetchVersions = memoize(versions => {
  return versions.map(version => {
    const [ id, isSeen ] = version
    return {
      id,
      isSeen,
      date: new Date(id),
    }
  })
})

function mapStateToProps(state, { wfModuleId }) {
  const { fetchWfModule, fetchModule } = getFetchWfModule(state)

  const wfModule = state.wfModules[String(wfModuleId)]
  const notificationsEnabled = wfModule ? wfModule.notifications : false

  return {
    fetchWfModuleId: fetchWfModule ? fetchWfModule.id : null,
    fetchWfModuleName: fetchModule ? fetchModule.name : null,
    fetchVersions: fetchWfModule ? getFetchVersions(fetchWfModule.versions.versions || []) : null,
    selectedFetchVersionId: fetchWfModule ? fetchWfModule.versions.selected : null,
    isAnonymous: state.workflow.is_anonymous,
    notificationsEnabled,
  }
}

function mapDispatchToProps(dispatch) {
  return {
    onChangeFetchVersionId(wfModuleId, versionId) {
      dispatch(setDataVersionAction(wfModuleId, versionId))
    },

    onChangeNotificationsEnabled(wfModuleId, isEnabled) {
      dispatch(updateWfModuleAction(wfModuleId, { notifications: isEnabled }))
    },
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(DataVersionModal)
