import React from 'react'
import PropTypes from 'prop-types'

/**
 * List of page ({ path, title }) <a> elements, with the active page a <span>
 */
export default function SidebarNav (props) {
  const { pages, activePath } = props

  return (
    <nav className='sidebar-nav'>
      <ul>
        {pages.map(({ path, title }) => (
          <li key={path}>
            {path === activePath ? (
              <span>{title}</span>
            ) : (
              <a href={path}>{title}</a>
            )}
          </li>
        ))}
      </ul>
    </nav>
  )
}
SidebarNav.propTypes = {
  pages: PropTypes.arrayOf(
    PropTypes.shape({
      path: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired
    }).isRequired
  ).isRequired,
  activePath: PropTypes.string.isRequired
}
