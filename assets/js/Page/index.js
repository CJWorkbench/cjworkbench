import React from 'react'
import PropTypes from 'prop-types'
import MainNav from './MainNav'

export function Page (props) {
  const { children } = props
  return (
    <div className='page'>{children}</div>
  )
}
Page.propTypes = {
  children: PropTypes.node.isRequired
}

export { MainNav }
