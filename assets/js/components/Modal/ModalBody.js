import PropTypes from 'prop-types'

export default function ModalBody ({ children }) {
  return <div className='modal-body'>{children}</div>
}
ModalBody.propTypes = {
  children: PropTypes.node.isRequired
}
