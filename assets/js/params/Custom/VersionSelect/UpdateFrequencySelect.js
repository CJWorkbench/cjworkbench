import React from 'react'
import PropTypes from 'prop-types'
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { timeDifference } from '../../../utils'
import { trySetWfModuleAutofetchAction, setWfModuleNotificationsAction } from '../../../workflow-reducer'
import { connect } from 'react-redux'
import { withI18n } from '@lingui/react'

export const UpdateFrequencySelect = withI18n()(class UpdateFrequencySelect extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    workflowId: PropTypes.number.isRequired,
    wfModuleId: PropTypes.number.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    lastCheckDate: PropTypes.instanceOf(Date), // null if never updated
    isAutofetch: PropTypes.bool.isRequired,
    fetchInterval: PropTypes.number.isRequired,
    isEmailUpdates: PropTypes.bool.isRequired,
    setEmailUpdates: PropTypes.func.isRequired, // func(wfModuleId, isEmailUpdates) => undefined
    trySetAutofetch: PropTypes.func.isRequired // func(wfModuleId, isAutofetch, fetchInterval) => Promise[response]
  }

  state = {
    isModalOpen: false,
    quotaExceeded: null // JSON response -- contains autofetch info iff we exceeded quota
  }

  handleClickOpenModal = (ev) => {
    if (ev && ev.preventDefault) ev.preventDefault() // <a> => do not change URL
    if (this.props.isReadOnly) return
    if (this.props.isAnonymous) return

    this.setState({
      isModalOpen: true
    })
  }

  handleCloseModal = () => {
    this.setState({
      isModalOpen: false
    })
  }

  setEmailUpdates = (isEmailUpdates) => {
    const { setEmailUpdates, wfModuleId } = this.props
    setEmailUpdates(wfModuleId, isEmailUpdates)
  }

  trySetAutofetch = (isAutofetch, fetchInterval) => {
    const { trySetAutofetch, wfModuleId } = this.props
    return trySetAutofetch(wfModuleId, isAutofetch, fetchInterval)
  }

  render () {
    const { i18n, lastCheckDate, isAutofetch, fetchInterval, isEmailUpdates, workflowId, wfModuleId } = this.props
    const { isModalOpen } = this.state

    return (
      <div className='update-frequency-select'>
        <div className='update-option'>
          <span className='version-box-option'>Update </span>
          <a
            href='#'
            title='change auto-update settings'
            className='content-1 ml-1 action-link'
            onClick={this.handleClickOpenModal}
          >
            {isAutofetch ? 'Auto' : 'Manual'}
          </a>
        </div>
        {lastCheckDate ? (
          <div className='last-checked'>
            Checked <time dateTime={this.props.lastCheckDate.toISOString()}>{timeDifference(lastCheckDate, Date.now(), i18n)}</time>
          </div>
        ) : null}
        {isModalOpen ? (
          <UpdateFrequencySelectModal
            workflowId={workflowId}
            wfModuleId={wfModuleId}
            isEmailUpdates={isEmailUpdates}
            isAutofetch={isAutofetch}
            fetchInterval={fetchInterval}
            setEmailUpdates={this.setEmailUpdates}
            trySetAutofetch={this.trySetAutofetch}
            onClose={this.handleCloseModal}
          />
        ) : null}
      </div>
    )
  }
})

const mapStateToProps = (state, ownProps) => {
  const workflow = state.workflow || {}
  const wfModule = state.wfModules[String(ownProps.wfModuleId)] || {}
  // We need a "default" value for everything: wfModule might be a placeholder

  const lastCheckString = wfModule.last_update_check // JSON has no date -- that's a STring
  const lastCheckDate = lastCheckString ? new Date(Date.parse(lastCheckString)) : null

  return {
    lastCheckDate,
    workflowId: workflow.id,
    isReadOnly: workflow.read_only,
    isAnonymous: workflow.is_anonymous,
    isEmailUpdates: wfModule.notifications || false,
    isAutofetch: wfModule.auto_update_data || false,
    fetchInterval: wfModule.update_interval || 86400
  }
}

const mapDispatchToProps = {
  trySetAutofetch: trySetWfModuleAutofetchAction,
  setEmailUpdates: setWfModuleNotificationsAction
}

export default connect(mapStateToProps, mapDispatchToProps)(UpdateFrequencySelect)
