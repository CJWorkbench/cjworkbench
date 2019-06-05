import React from 'react'
import PropTypes from 'prop-types'

export default function String_({ upstreamValue, name, secretLogic, submitSecret, deleteSecret }) {
  return (
    <div>STRING</div>
  )
}
String_.propTypes = {
  secretLogic: PropTypes.shape({
    provider: PropTypes.oneOf([ 'string' ]),
    label: PropTypes.string.isRequired,
    placeholder: PropTypes.string.isRequired,
    help: PropTypes.string.isRequired,
    helpUrl: PropTypes.string.isRequired,
    helpUrlPrompt: PropTypes.string.isRequired,
  })
}
