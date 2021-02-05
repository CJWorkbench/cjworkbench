import React from 'react'
import PropTypes from 'prop-types'
import MainNavHeader from './MainNavHeader'
import TopPaths from './TopPaths'
import BottomPaths from './BottomPaths'

export default function MainNav (props) {
  const [open, toggleOpen] = React.useReducer(open => !open, false)
  const { currentPath, user } = props

  return (
    <nav className={`main-nav${open ? ' open' : ''}`}>
      <MainNavHeader
        href={currentPath === '/workflows' ? null : '/workflows'}
        onToggleOpen={toggleOpen}
      />
      <TopPaths currentPath={currentPath} />
      <BottomPaths user={user} currentPath={currentPath} />
    </nav>
  )
}
MainNav.propTypes = {
  currentPath: PropTypes.string.isRequired,
  user: PropTypes.shape({
    stripeCustomerId: PropTypes.string.isRequired
  }) // or null
}
