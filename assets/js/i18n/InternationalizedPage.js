import React from 'react'
import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'
import { I18nProvider } from '@lingui/react'

export default function InternationalizedPage (props) {
  const { children } = props
  return <I18nProvider i18n={i18n}>{children}</I18nProvider>
}
InternationalizedPage.propTypes = {
  children: PropTypes.node.isRequired
}
