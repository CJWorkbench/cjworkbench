import React from 'react'
import PropTypes from 'prop-types'
import MainNavHeader from './MainNavHeader'
import TopPaths from './TopPaths'
import BottomPaths from './BottomPaths'

export default function Sidebar (props) {
  const { currentPath, user } = props

  return (
    <nav className='main-nav'>
      <MainNavHeader href={currentPath === '/workflows' ? null : '/workflows'} />
      <TopPaths currentPath={currentPath} />
      <BottomPaths user={user} currentPath={currentPath} />
    </nav>
  )
}
Sidebar.propTypes = {
  currentPath: PropTypes.string.isRequired,
  user: PropTypes.shape({
    stripeCustomerId: PropTypes.string.isRequired
  }) // or null
}
