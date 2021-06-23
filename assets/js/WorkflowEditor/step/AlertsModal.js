import React from 'react'
import PropTypes from 'prop-types'
import { t, Trans } from '@lingui/macro'
import { useDispatch } from 'react-redux'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../components/Modal'
import { setStepNotificationsAction } from '../../workflow-reducer'

export default function AlertsModal (props) {
  const { stepId, checked, onClose } = props
  const dispatch = useDispatch()

  const handleChangeAlerts = React.useCallback(
    (ev) => { dispatch(setStepNotificationsAction(stepId, ev.target.checked)) },
    [stepId, dispatch]
  )

  return (
    <Modal className='alerts-modal' isOpen fade={false} toggle={onClose}>
      <ModalHeader toggle={onClose}>
        <Trans id='js.WorkflowEditor.step.AlertsModal.header'>
          Alerts
        </Trans>
      </ModalHeader>
      <ModalBody>
        <div className='alerts-toggle'>
          <div className='toggle'>
            <input
              id='alertsModalToggle'
              type='checkbox'
              name='notifications'
              checked={checked}
              onChange={handleChangeAlerts}
            />
            <label htmlFor='alertsModalToggle' className='toggle' />
          </div>
          <label className='onoff' htmlFor='alertsModalToggle'>
            <i className={checked ? 'icon-notification' : 'icon-no-notification'} />
            {' '}
            {checked
              ? <Trans id='js.WorkflowEditor.step.AlertsModal.on'>Alerts are ON</Trans>
              : <Trans id='js.WorkflowEditor.step.AlertsModal.off'>Alerts are OFF</Trans>}
          </label>
        </div>
        <p>
          <Trans id='js.WorkflowEditor.step.AlertsModal.description'>
            When alerts are ON, Workbench emails you each time this step's output changes.
          </Trans>
        </p>
      </ModalBody>
      <ModalFooter>
        <button
          type='button'
          className='close'
          title={t({
            id: 'js.WorkflowEditor.steps.AlertsModal.footer.closeButton.hoverText',
            message: 'Close'
          })}
          onClick={onClose}
        >
          <Trans id='js.WorkflowEditor.steps.AlertsModal.footer.closeButton'>
            Close
          </Trans>
        </button>
      </ModalFooter>
    </Modal>
  )
}
AlertsModal.propTypes = {
  stepId: PropTypes.number.isRequired, // TODO slug
  checked: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired // func() => undefined
}
