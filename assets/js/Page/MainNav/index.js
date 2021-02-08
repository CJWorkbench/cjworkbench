import React from 'react'
import PropTypes from 'prop-types'
import MainNavFragment from './MainNavFragment'

export default function MainNav (props) {
  const { currentPath, user } = props

  return (
    <nav className='main-nav'>
      <MainNavFragment
        currentPath={currentPath}
        user={user}
      />
    </nav>
  )
}
MainNav.propTypes = {
  currentPath: PropTypes.string.isRequired,
  user: PropTypes.object // or null
}
