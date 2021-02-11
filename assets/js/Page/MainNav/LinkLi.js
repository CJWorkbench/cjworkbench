import PropTypes from 'prop-types'

export default function LinkLi (props) {
  const { href, isOpen, title, children } = props

  const className = [
    isOpen ? 'open' : null,
    children ? 'parent' : null
  ].filter(n => n).join(' ')

  return (
    <li className={className}>
      <a href={isOpen ? null : href}>{title}</a>
      {isOpen ? children : null}
    </li>
  )
}
LinkLi.propTypes = {
  href: PropTypes.string.isRequired,
  isOpen: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node // or undefined
}
