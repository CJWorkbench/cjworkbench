import React from 'react'
import PropTypes from 'prop-types'

export default function ModalBody ({ children }) {
  return (
    <div className='modal-body' children={children} />
  )
}
ModalBody.propTypes = {
  children: PropTypes.node.isRequired
}
