import React from 'react'
import { Trans } from '@lingui/macro'
import LocaleSwitcher from '../../i18n/LocaleSwitcher'

export default function SetLocaleLink () {
  const [isDialogOpen, setDialogOpen] = React.useState(false)

  const handleClick = React.useCallback(ev => {
    ev.preventDefault()
    setDialogOpen(true)
  }, [setDialogOpen])
  const handleClickClose = React.useCallback(ev => {
    ev.preventDefault()
    setDialogOpen(false)
  }, [setDialogOpen])

  return (
    <li className={isDialogOpen ? 'open' : null}>
      <a href='#' onClick={handleClick}>
        <Trans id='js.Page.MainNav.SetLocaleLink.title'>Language</Trans>
      </a>
      {isDialogOpen ? (
        <LocaleSwitcher closeModal={handleClickClose} />
      ) : null}
    </li>
  )
}
