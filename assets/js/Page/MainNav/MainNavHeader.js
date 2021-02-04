import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'

export default function MainNavHeader (props) {
  const { href } = props
  return (
    <header>
      <a href={href}>
        <img
          src={`${window.STATIC_URL}images/workbench-logo-white.svg`}
          alt={t({ id: 'js.Page.MainNav.Header.brandName', message: 'Workbench' })}
        />
      </a>
    </header>
  )
}
MainNavHeader.propTypes = {
  href: PropTypes.string // or null
}
