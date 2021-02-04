import React from 'react'
import { Trans } from '@lingui/macro'
import { csrfToken } from '../../utils'

export default function LogoutLink () {
  const logoutFormRef = React.useRef(null)
  const handleClick = React.useCallback(ev => {
    ev.preventDefault()
    const logoutForm = logoutFormRef.current
    if (logoutForm) {
      logoutForm.submit()
    }
  }, [logoutFormRef])

  return (
    <li>
      <a href='#' onClick={handleClick}>
        <Trans id='js.Page.MainNav.logout'>Log Out</Trans>
      </a>
      <form className='hidden' ref={logoutFormRef} method='post' action='/account/logout/'>
        <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken} />
        <input type='submit' />
      </form>
    </li>
  )
}
