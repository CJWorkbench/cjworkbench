import { useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import propTypes from '../propTypes'
import VersionSelect from './Custom/VersionSelect'
import UploadApiModal from './File/UploadApiModal'
import { Trans, t } from '@lingui/macro'

function isFieldVersionSelect ({ type, idName }) {
  return type === 'custom' && idName === 'version_select'
}

function isFieldStatic ({ type, idName }) {
  return (
    type === 'statictext' ||
    (type === 'custom' &&
      (idName === 'celledits' ||
        idName === 'reorder-history' ||
        idName === 'version_select'))
  )
}

function isFileField ({ type }) {
  return type === 'file'
}

export default function ParamsFormFooter ({
  workflowId,
  stepId,
  stepSlug,
  isStepBusy,
  isReadOnly,
  isOwner,
  fields,
  isEditing
}) {
  const [isUploadApiModalOpen, setIsUploadApiModalOpen] = useState(false)
  const handleClickOpenUploadApiModal = useCallback(
    () => setIsUploadApiModalOpen(true),
    [setIsUploadApiModalOpen]
  )
  const handleClickCloseUploadApiModal = useCallback(
    () => setIsUploadApiModalOpen(false),
    [setIsUploadApiModalOpen]
  )

  const versionSelectField = fields.find(isFieldVersionSelect)
  if (versionSelectField) {
    return (
      <VersionSelect
        stepId={stepId}
        isStepBusy={isStepBusy}
        isReadOnly={isReadOnly}
        name={versionSelectField.idName}
        label={versionSelectField.name}
      />
    )
  }

  // Maybe a submit button; maybe nothing
  if (isReadOnly) return null
  if (fields.every(isFieldStatic)) return null

  const fileField = fields.find(isFileField)
  return (
    <div className='params-form-footer'>
      {fileField && isOwner
        ? (
          <button
            type='button'
            onClick={handleClickOpenUploadApiModal}
            name='open-upload-api'
            title={t({
              id: 'js.params.Custom.File.uploadApi.hoverText',
              message: 'Open upload API instructions'
            })}
          >
            <Trans id='js.params.Custom.File.uploadApi.button'>API</Trans>
          </button>
          )
        : null}
      {isUploadApiModalOpen
        ? (
          <UploadApiModal
            workflowId={workflowId}
            stepSlug={stepSlug}
            onClickClose={handleClickCloseUploadApiModal}
          />
          )
        : null}
      <button name='submit' type='submit' disabled={!isEditing}>
        <i className='icon-play' />
      </button>
    </div>
  )
}
ParamsFormFooter.propTypes = {
  workflowId: propTypes.workflowId.isRequired,
  stepId: PropTypes.number.isRequired,
  stepSlug: PropTypes.string.isRequired,
  isStepBusy: PropTypes.bool.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  isOwner: PropTypes.bool.isRequired,
  fields: PropTypes.arrayOf(
    PropTypes.shape({
      type: PropTypes.string.isRequired,
      idName: PropTypes.string.isRequired
    }).isRequired
  ).isRequired,
  isEditing: PropTypes.bool.isRequired
}
