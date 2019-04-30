import React from 'react'
import PropTypes from 'prop-types'


export default function DeprecationMessage ({ helpUrl, message }) {
  if (!message) return null

  return (
    <div className='module-deprecated'>
      <p>{message}</p>
      <a target='_blank' href={helpUrl}>Learn how to replace this module</a>
    </div>
  )
}
DeprecationMessage.propTypes = {
  helpUrl: PropTypes.string.isRequired,
  message: PropTypes.string // null/undefined means "not deprecated"
}
