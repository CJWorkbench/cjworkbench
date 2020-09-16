import React from 'react'
import PropTypes from 'prop-types'
import OAuth from './OAuth'
import String_ from './String'

const Components = {
  oauth1a: OAuth,
  oauth2: OAuth,
  string: String_
}

export default function Secret ({ isReadOnly, isOwner, name, fieldId, secretMetadata, secretLogic, submitSecret, deleteSecret, startCreateSecret }) {
  const Component = Components[secretLogic.provider]

  return (
    <Component
      isReadOnly={isReadOnly}
      isOwner={isOwner}
      name={name}
      fieldId={fieldId}
      secretMetadata={secretMetadata}
      secretLogic={secretLogic}
      submitSecret={submitSecret}
      startCreateSecret={startCreateSecret}
      deleteSecret={deleteSecret}
    />
  )
}
Secret.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired, // <input name=...>
  fieldId: PropTypes.string.isRequired, // <input id=...>
  secretMetadata: PropTypes.object, // the _only_ value is the upstream one; may be null/undefined
  submitSecret: PropTypes.func.isRequired, // func(name, secret) => undefined
  startCreateSecret: PropTypes.func.isRequired, // func(name) => undefined
  deleteSecret: PropTypes.func.isRequired, // func(name) => undefined
  secretLogic: PropTypes.shape({
    provider: PropTypes.oneOf(['oauth1a', 'oauth2', 'string'])
    // Plus provider-specific stuff
  }).isRequired
}
