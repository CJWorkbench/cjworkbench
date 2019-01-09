import React from 'react'
import PropTypes from 'prop-types'
import SubmitButton from './SubmitButton'
import VersionSelect, { VersionSelectSimpler } from './Custom/VersionSelect'

function isFieldVersionSelect ({ type, id_name }) {
  return type === 'custom' && (id_name === 'version_select' || id_name === 'version_select_simpler')
}

function isFieldEditable ({ type, id_name }) {
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
  if (id_name in StaticCustomIdNames) return false

  return true
}

export default function ParamsFormFooter ({ wfModuleId, isWfModuleBusy, isReadOnly, fields, isEditing }) {
  const field = fields.find(isFieldVersionSelect)

  if (field) {
    const Component = field.id_name === 'version_select' ? VersionSelect : VersionSelectSimpler
    return (
      <Component
        wfModuleId={wfModuleId}
        isWfModuleBusy={isWfModuleBusy}
        isReadOnly={isReadOnly}
        name={field.id_name}
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
  wfModuleId: PropTypes.number.isRequired,
  isWfModuleBusy: PropTypes.bool.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  fields: PropTypes.arrayOf(PropTypes.shape({
    type: PropTypes.string.isRequired,
    id_name: PropTypes.string.isRequired,
  }).isRequired).isRequired,
  isEditing: PropTypes.bool.isRequired,
}

