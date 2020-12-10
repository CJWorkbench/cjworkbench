import React from 'react'
import PropTypes from 'prop-types'
import { en, el } from 'make-plural/plurals'
import { i18n } from '@lingui/core'
import { I18nProvider } from '@lingui/react'
import { currentLocaleId } from './locales'
import Spinner from '../Spinner'

__webpack_public_path__ = window.STATIC_URL + 'bundles/' // eslint-disable-line

async function loadLocale (localeId) {
  const { messages } = await import(
    /* webpackChunkName: "[request]" */
    `@lingui/loader!../../locale/${localeId}/messages.po`
  )
  i18n.loadLocaleData({
    en: { plurals: en },
    el: { plurals: el }
  })
  i18n.load(localeId, messages)
  i18n.activate(localeId)
  return i18n
}

function useActivatedI18n (localeId) {
  const [i18n, setI18n] = React.useState(null)

  React.useEffect(() => {
    loadLocale(currentLocaleId).then(setI18n)
  }, [])

  return i18n
}

export default function InternationalizedPage (props) {
  const { children } = props
  const i18n = useActivatedI18n(currentLocaleId)

  if (i18n === null) {
    return <Spinner />
  }

  return (
    <I18nProvider i18n={i18n} forceRenderOnLocaleChange={false}>
      {children}
    </I18nProvider>
  )
}
InternationalizedPage.propTypes = {
  children: PropTypes.node.isRequired
}
