import React from 'react'
import PropTypes from 'prop-types'
import SubmitButton from './SubmitButton'
import VersionSelect, { VersionSelectSimpler } from './Custom/VersionSelect'

function isFieldVersionSelect ({ type, idName }) {
  return type === 'custom' && (idName === 'version_select' || idName === 'version_select_simpler')
}

function isFieldEditable ({ type, idName }) {
  const StaticTypes = {
    statictext: null
  }
  const StaticCustomIdNames = {
    celledits: null,
    'reorder-history': null,
    version_select: null,
    version_select_simpler: null
  }

  if (type in StaticTypes) return false
  if (idName in StaticCustomIdNames) return false

  return true
}

export default function ParamsFormFooter ({ stepId, isStepBusy, isReadOnly, fields, isEditing }) {
  const field = fields.find(isFieldVersionSelect)

  if (field) {
    const Component = field.idName === 'version_select' ? VersionSelect : VersionSelectSimpler
    return (
      <Component
        stepId={stepId}
        isStepBusy={isStepBusy}
        isReadOnly={isReadOnly}
        name={field.idName}
        label={field.name}
      />
    )
  } else {
    // Maybe a submit button; maybe nothing
    if (isReadOnly) return null
    if (fields === null || fields.filter(isFieldEditable).length === 0) return null
    return <SubmitButton name='submit' disabled={!isEditing} />
  }
}
ParamsFormFooter.propTypes = {
  stepId: PropTypes.number.isRequired,
  isStepBusy: PropTypes.bool.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  fields: PropTypes.arrayOf(PropTypes.shape({
    type: PropTypes.string.isRequired,
    idName: PropTypes.string.isRequired
  }).isRequired).isRequired,
  isEditing: PropTypes.bool.isRequired
}
