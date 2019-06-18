import React from 'react'
import PropTypes from 'prop-types'
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { timeDifference } from '../../../utils'
import { updateWfModuleAction, setWfModuleNotificationsAction } from '../../../workflow-reducer'
import { connect } from 'react-redux'

export class UpdateFrequencySelect extends React.PureComponent {
  static propTypes = {
    wfModuleId: PropTypes.number.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    lastCheckDate: PropTypes.instanceOf(Date), // null if never updated
    settings: PropTypes.shape({
      isAutoUpdate: PropTypes.bool.isRequired,
      isEmailUpdates: PropTypes.bool.isRequired,
      timeNumber: PropTypes.number.isRequired,
      timeUnit: PropTypes.oneOf([ 'minutes', 'hours', 'days', 'weeks' ]).isRequired,
    }).isRequired,
    updateSettings: PropTypes.func.isRequired, // func({ isAutoUpdate, timeNumber, timeUnit }) -> undefined
  }

  constructor(props) {
    super(props);
    this.state = {
      isModalOpen: false,
    }
  }

  onOpenModal = (ev) => {
    if (ev && ev.preventDefault) ev.preventDefault() // <a> => do not change URL
    if (this.props.isReadOnly) return
    if (this.props.isAnonymous) return

    this.setState({
      isModalOpen: true,
    })
  }

  onSubmit = (settings) => {
    this.props.updateSettings(settings)
    // TODO keep modal open until server responds with OK?
    this.setState({
      isModalOpen: false,
    })
  }

  onCancel = () => {
    this.setState({
      isModalOpen: false,
    })
  }

  render() {
    const lastChecked = this.props.lastCheckDate ? (
      <div className="last-checked">
        Checked <time time={this.props.lastCheckDate.toISOString()}>{timeDifference(this.props.lastCheckDate, Date.now())}</time>
      </div>
    ) : null

    const autoOrManual = this.props.settings.isAutoUpdate ? 'Auto' : 'Manual'

    const maybeModal = this.state.isModalOpen ? (
        <UpdateFrequencySelectModal
          {...this.props.settings}
          setEmailUpdates={this.props.setEmailUpdates}
          onCancel={this.onCancel}
          onSubmit={this.onSubmit}
          />
    ) : null

    return (
      <div className='update-frequency-select'>
        <div className="update-option">
          <span className='version-box-option'>Update </span>
          <a href="#" title="change auto-update settings" className='content-1 ml-1 action-link' onClick={this.onOpenModal}>{autoOrManual}</a>
        </div>
        {lastChecked}
        {maybeModal}
      </div>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const workflow = state.workflow || {}
  const wfModule = state.wfModules[String(ownProps.wfModuleId)] || {}
  // We need a "default" value for everything: wfModule might be a placeholder

  const lastCheckString = wfModule.last_update_check // JSON has no date -- that's a STring
  const lastCheckDate = lastCheckString ? new Date(Date.parse(lastCheckString)) : null

  return {
    lastCheckDate,
    isReadOnly: workflow.read_only,
    isAnonymous: workflow.is_anonymous,
    settings: {
      isAutoUpdate: wfModule.auto_update_data || false,
      isEmailUpdates: wfModule.notifications || false,
      timeNumber: wfModule.update_interval || 1,
      timeUnit: wfModule.update_units || 'days',
    }
  }
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateSettings: (settings) => {
      const action = updateWfModuleAction(ownProps.wfModuleId, {
        auto_update_data: settings.isAutoUpdate,
        update_interval: settings.timeNumber,
        update_units: settings.timeUnit,
      })
      dispatch(action)
    },
    setEmailUpdates: (wantEmails) => {
      return dispatch(setWfModuleNotificationsAction(ownProps.wfModuleId, wantEmails))
    }
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(UpdateFrequencySelect)
