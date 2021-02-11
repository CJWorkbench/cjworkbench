import PropTypes from 'prop-types'

export default function ModalFooter ({ children }) {
  return <div className='modal-footer'>{children}</div>
}
ModalFooter.propTypes = {
  children: PropTypes.node.isRequired
}
