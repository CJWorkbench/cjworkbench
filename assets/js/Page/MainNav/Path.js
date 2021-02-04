import React from 'react'
import PropTypes from 'prop-types'

function OpenLink ({ children }) {
  return <span>{children}</span>
}

function UnopenLink ({ href, children }) {
  return <a href={href}>{children}</a>
}

function Subpath (props) {
  const { currentPath, path, title } = props
  const isOpen = path === currentPath
  const Link = isOpen ? OpenLink : UnopenLink

  return (
    <li className={isOpen ? 'open' : null}>
      <Link href={path}>{title}</Link>
    </li>
  )
}

export default function Path (props) {
  const { currentPath, path, match, title, subPaths, user } = props
  const isOpen = match ? match(currentPath) : currentPath === path
  const pathString = path.apply ? path.apply({ user }) : path
  const Link = isOpen ? OpenLink : UnopenLink

  return (
    <li className={isOpen ? 'open' : null}>
      <Link href={pathString}>
        {title}
        {subPaths ? (
          <ul className='subpaths'>
            {subPaths.map(({ path, title }) => (
              <Subpath
                key={path}
                currentPath={currentPath}
                path={path}
                title={title}
              />
            ))}
          </ul>
        ) : null}
      </Link>
    </li>
  )
}
Path.propTypes = {
  currentPath: PropTypes.string.isRequired,
  path: PropTypes.oneOfType([
    PropTypes.string.isRequired,
    PropTypes.func.isRequired // func({ user }) => string
  ]).isRequired,
  match: PropTypes.func, // func(currentPath) => bool, or null for func(currentPath) => currentPath == path
  title: PropTypes.string.isRequired,
  subPaths: PropTypes.arrayOf(
    PropTypes.shape({
      path: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired
    }).isRequired
  ), // or null
  user: PropTypes.object // or null
}
