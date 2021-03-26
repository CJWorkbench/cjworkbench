import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../../../propTypes'
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { timeDifference } from '../../../utils'
import {
  trySetStepAutofetchAction,
  setStepNotificationsAction
} from '../../../workflow-reducer'
import { connect } from 'react-redux'
import { i18n } from '@lingui/core'
import { Trans, t } from '@lingui/macro'
import selectIsAnonymous from '../../../selectors/selectIsAnonymous'
import selectIsReadOnly from '../../../selectors/selectIsReadOnly'

export class UpdateFrequencySelect extends React.PureComponent {
  static propTypes = {
    workflowId: propTypes.workflowId.isRequired,
    stepId: PropTypes.number.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    lastCheckDate: PropTypes.instanceOf(Date), // null if never updated
    isAutofetch: PropTypes.bool.isRequired,
    fetchInterval: PropTypes.number.isRequired,
    isEmailUpdates: PropTypes.bool.isRequired,
    setEmailUpdates: PropTypes.func.isRequired, // func(stepId, isEmailUpdates) => undefined
    trySetAutofetch: PropTypes.func.isRequired // func(stepId, isAutofetch, fetchInterval) => Promise[response]
  }

  state = {
    isModalOpen: false,
    quotaExceeded: null // JSON response -- contains autofetch info iff we exceeded quota
  }

  handleClickOpenModal = ev => {
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

  setEmailUpdates = isEmailUpdates => {
    const { setEmailUpdates, stepId } = this.props
    setEmailUpdates(stepId, isEmailUpdates)
  }

  trySetAutofetch = (isAutofetch, fetchInterval) => {
    const { trySetAutofetch, stepId } = this.props
    return trySetAutofetch(stepId, isAutofetch, fetchInterval)
  }

  render () {
    const {
      lastCheckDate,
      isAutofetch,
      fetchInterval,
      isEmailUpdates,
      workflowId,
      stepId
    } = this.props
    const { isModalOpen } = this.state

    return (
      <div className='update-frequency-select'>
        <div className='update-option'>
          <span className='version-box-option'>
            <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelect.update'>
              Update
            </Trans>{' '}
          </span>
          <a
            href='#'
            title={t({
              id:
                'js.params.Custom.VersionSelect.UpdateFrequencySelect.changeUpdateSettings.hoverText',
              message: 'change auto-update settings'
            })}
            className='content-1 ml-1 action-link'
            onClick={this.handleClickOpenModal}
          >
            {isAutofetch
              ? (
                <Trans
                  id='js.params.Custom.VersionSelect.UpdateFrequencySelect.auto'
                  comment="Appears just after 'js.params.Custom.VersionSelect.UpdateFrequencySelect.update'"
                >
                  Auto
                </Trans>
                )
              : (
                <Trans
                  id='js.params.Custom.VersionSelect.UpdateFrequencySelect.manual'
                  comment="Appears just after 'js.params.Custom.VersionSelect.UpdateFrequencySelect.update'"
                >
                  Manual
                </Trans>
                )}
          </a>
        </div>
        {lastCheckDate
          ? (
            <div className='last-checked'>
              <Trans
                id='js.params.Custom.VersionSelect.UpdateFrequencySelect.lastChecked'
                comment="The parameter is a time difference (i.e. something like '4h ago'. The tag is a <time> tag."
              >
                Checked{' '}
                <time dateTime={this.props.lastCheckDate.toISOString()}>
                  {timeDifference(lastCheckDate, Date.now(), i18n)}
                </time>
              </Trans>
            </div>
            )
          : null}
        {isModalOpen
          ? (
            <UpdateFrequencySelectModal
              workflowId={workflowId}
              stepId={stepId}
              isEmailUpdates={isEmailUpdates}
              isAutofetch={isAutofetch}
              fetchInterval={fetchInterval}
              setEmailUpdates={this.setEmailUpdates}
              trySetAutofetch={this.trySetAutofetch}
              onClose={this.handleCloseModal}
            />
            )
          : null}
      </div>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const workflow = state.workflow || {}
  const step = state.steps[String(ownProps.stepId)] || {}
  // We need a "default" value for everything: step might be a placeholder

  const lastCheckString = step.last_update_check // JSON has no date -- that's a STring
  const lastCheckDate = lastCheckString
    ? new Date(Date.parse(lastCheckString))
    : null

  return {
    lastCheckDate,
    workflowId: workflow.id,
    isReadOnly: selectIsReadOnly(state),
    isAnonymous: selectIsAnonymous(state),
    isEmailUpdates: step.notifications || false,
    isAutofetch: step.auto_update_data || false,
    fetchInterval: step.update_interval || 86400
  }
}

const mapDispatchToProps = {
  trySetAutofetch: trySetStepAutofetchAction,
  setEmailUpdates: setStepNotificationsAction
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(UpdateFrequencySelect)
