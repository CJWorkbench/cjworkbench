import React from 'react'
import PropTypes from 'prop-types'
import MainNavHeader from './MainNavHeader'
import TopPaths from './TopPaths'
import BottomPaths from './BottomPaths'

export default function MainNavFragment (props) {
  const { currentPath, user } = props

  return (
    <>
      <MainNavHeader href={currentPath === '/workflows' ? null : '/workflows'} />
      <TopPaths currentPath={currentPath} />
      <BottomPaths user={user} currentPath={currentPath} />
    </>
  )
}
MainNavFragment.propTypes = {
  currentPath: PropTypes.string.isRequired,
  user: PropTypes.shape({
    stripeCustomerId: PropTypes.string.isRequired
  }) // or null
}
