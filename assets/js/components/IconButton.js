import PropTypes from 'prop-types'

export default function IconButton (props) {
  const { name, title, children, disabled = false, onClick = null } = props

  return (
    <button
      className='icon-button'
      title={title}
      name={name}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
IconButton.propTypes = {
  name: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.element.isRequired,
  disabled: PropTypes.bool,
  onClick: PropTypes.func
}
