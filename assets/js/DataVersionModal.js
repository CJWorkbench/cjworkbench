import React from 'react'
import PropTypes from 'prop-types'
import Modal from 'reactstrap/lib/Modal'
import ModalHeader from 'reactstrap/lib/ModalHeader'
import ModalBody from 'reactstrap/lib/ModalBody'
import ModalFooter from 'reactstrap/lib/ModalFooter'
import memoize from 'memoize-one'
import { setDataVersionAction, updateWfModuleAction } from './workflow-reducer'
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

/**
 * Return AP-style date in the user's time zone, but with the date before the
 * time.
 *
 * For instance: "June 22, 2018 – 10:35 a.m."
 */
function formatDate(date) {
  const mon = Months[date.getMonth()]
  const dd = date.getDate()
  const yyyy = date.getFullYear()
  let hh = date.getHours()
  const mm = String(100 + date.getMinutes()).slice(1) // 0-padded
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

    return (
      <form onSubmit={this.onSubmit} className={`notifications ${className}`}>
        <p className="status"><i className="icon icon-notification"/> Alerts are <strong>{checked ? 'on' : 'off'}</strong></p>
        <p className="description">{ checked ? (
          'If the output of this module changes, I will receive an email'
        ) : (
          'Turn alerts ON to receive an email if the output of this module changes'
        )}</p>
        <label>
          <input name="notifications-enabled" type="checkbox" checked={checked} onChange={this.onChange}/>
          <span className="action">{checked ? 'Turn off' : 'Turn on'}</span>
        </label>
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
    selectedFetchVersionId: PropTypes.string.isRequired,
    wfModuleId: PropTypes.number.isRequired,
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
      notificationsEnabled,
    } = this.props

    return (
      <Modal className="data-versions-modal" isOpen={true} fade={false} toggle={onClose}>
        <ModalHeader toggle={onClose}>Data Versions </ModalHeader>
        <ModalBody>
          <form onSubmit={this.onSubmit} onCancel={this.onClose}>
            <p className="introduction">These are the versions of “{fetchWfModuleName}” that we have stored:</p>
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
          <NotificationsForm
            notificationsEnabled={notificationsEnabled}
            onSubmit={this.onChangeNotificationsEnabled}
            />
          <button
            name="load"
            disabled={this.state.selectedFetchVersionId === this.props.selectedFetchVersionId}
            onClick={this.onSubmit}
            >Load</button>
        </ModalFooter>
      </Modal>
    )
  }
}

const getWorkflow = ({ workflow }) => workflow
/**
 * Find first WfModule that has a `.loads_data` ModuleVersion.
 */
const getFetchWfModule = createSelector([ getWorkflow ], (workflow) => {
  return (workflow.wf_modules || []).find(wfModule => {
    return wfModule.module_version && wfModule.module_version.module && wfModule.module_version.module.loads_data
  }) || null
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
  const fetchWfModule = getFetchWfModule(state)

  const wfModule = state.workflow.wf_modules.find(m => m.id === wfModuleId)
  const notificationsEnabled = wfModule ? wfModule.notifications : false

  return {
    fetchWfModuleId: fetchWfModule ? fetchWfModule.id : null,
    fetchWfModuleName: fetchWfModule ? fetchWfModule.module_version.module.name : null,
    fetchVersions: fetchWfModule ? getFetchVersions(fetchWfModule.versions.versions || []) : null,
    selectedFetchVersionId: fetchWfModule ? fetchWfModule.versions.selected : null,
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
