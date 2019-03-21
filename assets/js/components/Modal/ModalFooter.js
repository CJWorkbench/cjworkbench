import React from 'react'
import PropTypes from 'prop-types'

export default function ModalFooter ({ children }) {
  return (
    <div className='modal-footer' children={children} />
  )
}
ModalFooter.propTypes = {
  children: PropTypes.node.isRequired
}
