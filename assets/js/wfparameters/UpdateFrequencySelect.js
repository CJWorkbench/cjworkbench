import React from 'react'
import PropTypes from 'prop-types'
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { timeDifference } from '../utils'
import { updateWfModuleAction } from '../workflow-reducer'
import { connect } from 'react-redux'

export class UpdateFrequencySelect extends React.PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      isModalOpen: false,
    }
  }

  onOpenModal = (ev) => {
    if (ev && ev.preventDefault) ev.preventDefault() // <a> => do not change URL
    if (this.props.isReadOnly) return

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
      <div className="content-4 t-m-gray">
        Checked <time time={this.props.lastCheckDate.toISOString()}>{timeDifference(this.props.lastCheckDate, Date.now())}</time>
      </div>
    ) : null

    const autoOrManual = this.props.settings.isAutoUpdate ? 'auto' : 'manual'

    const maybeModal = this.state.isModalOpen ? (
        <UpdateFrequencySelectModal
          {...this.props.settings}
          onCancel={this.onCancel}
          onSubmit={this.onSubmit}
          />
    ) : null

    return (
      <div className='frequency-item'>
        <div>
          <span className='content-3 t-d-gray'>Update </span>
          <a href="#" title="change auto-update settings" className='content-3 ml-1 t-f-blue' onClick={this.onOpenModal}>{autoOrManual}</a>
        </div>
        {lastChecked}
        {maybeModal}
      </div>
    )
  }

}

UpdateFrequencySelect.propTypes = {
  wfModuleId: PropTypes.number.isRequired,
  lastCheckDate: PropTypes.instanceOf(Date), // null if never updated
  settings: PropTypes.shape({
    isAutoUpdate: PropTypes.bool.isRequired,
    isEmailUpdates: PropTypes.bool.isRequired,
    timeNumber: PropTypes.number.isRequired,
    timeUnit: PropTypes.oneOf([ 'minutes', 'hours', 'days', 'weeks' ]).isRequired,
  }).isRequired,
  updateSettings: PropTypes.func.isRequired, // func({ isAutoUpdate, isEmailUpdates, timeNumber, timeUnit }) -> undefined
}

const mapStateToProps = (state, ownProps) => {
  const workflow = state.workflow || {}
  const wfModules = workflow.wf_modules || {}
  const wfModule = wfModules.find(wfm => wfm.id === ownProps.wfModuleId) || {}
  // We need a "default" value for everything: wfModule might be a placeholder

  const lastCheckString = wfModule.last_update_check // JSON has no date -- that's a STring
  const lastCheckDate = lastCheckString ? new Date(Date.parse(lastCheckString)) : null

  return {
    lastCheckDate,
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
        notifications: settings.isEmailUpdates,
      })
      dispatch(action)
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(UpdateFrequencySelect)
