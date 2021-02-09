import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { csrfToken } from '../../utils'

export default function LogoutLinkLi (props) {
  const { nextPath } = props
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
        <input type='hidden' name='next' value={nextPath} />
        <input type='submit' />
      </form>
    </li>
  )
}
LogoutLinkLi.propTypes = {
  nextPath: PropTypes.string.isRequired
}
