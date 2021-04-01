import React from 'react'
import PropTypes from 'prop-types'
import propTypes from './propTypes'
import ShareUrl from './components/ShareUrl'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './components/Modal'
import { Trans } from '@lingui/macro'

function buildUrlString (workflowIdOrSecretId, stepSlug, ext) {
  const path = `/workflows/${workflowIdOrSecretId}/steps/${stepSlug}/current-result-table.${ext}`
  if (window.location.href === 'about:blank') {
    // allowing an out for testing (there is no window.location.href during test)
    return path
  } else {
    return new URL(path, window.location.href).href
  }
}

export default function ExportModal (props) {
  const { open, workflowIdOrSecretId, stepSlug, toggle } = props

  const csvUrlString = buildUrlString(workflowIdOrSecretId, stepSlug, 'csv')
  const jsonUrlString = buildUrlString(workflowIdOrSecretId, stepSlug, 'json')

  return (
    <Modal
      isOpen={open}
      className='export'
      toggle={toggle}
    >
      <ModalHeader>
        <Trans
          id='js.ExportModal.header.title'
          comment='This should be all-caps for styling reasons'
        >
          EXPORT DATA
        </Trans>
      </ModalHeader>
      <ModalBody>
        <dl>
          <dt>
            <Trans
              id='js.ExportModal.type.CSV'
              comment='"CSV" (all-caps) is a kind of file'
            >
              CSV
            </Trans>
          </dt>
          <dd>
            <ShareUrl url={csvUrlString} download />
          </dd>
          <dt>
            <Trans
              id='js.ExportModal.type.JSON'
              comment='"JSON" (all-caps) is a kind of file'
            >
              JSON
            </Trans>
          </dt>
          <dd>
            <ShareUrl url={jsonUrlString} download />
          </dd>
        </dl>
      </ModalBody>
      <ModalFooter>
        <button
          type='button'
          onClick={toggle}
          className='button-blue action-button test-done-button'
        >
          <Trans
            id='js.ExportModal.footer.doneButton'
            comment='Acts as closing button'
          >
            Done
          </Trans>
        </button>
      </ModalFooter>
    </Modal>
  )
}
ExportModal.propTypes = {
  open: PropTypes.bool.isRequired,
  workflowIdOrSecretId: propTypes.workflowId.isRequired, // to build download URLs
  stepSlug: PropTypes.string.isRequired, // to build download URLs
  toggle: PropTypes.func.isRequired
}
