import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import LinkLi from './LinkLi'
import SetLocaleLinkLi from './SetLocaleLinkLi'
import LogoutLinkLi from './LogoutLinkLi'

export default function BottomPaths (props) {
  const { currentPath, user } = props

  return (
    <ul>
      <LinkLi
        href={user && user.stripeCustomerId ? '/settings/billing' : '/settings/plan'}
        isOpen={/^\/settings\/(?:billing|plan)/.test(currentPath)}
        title={t({ id: 'js.Page.MainNav.plan-and-billing.title', message: 'Plan & Billing' })}
      >
        <ul>
          <LinkLi
            href='/settings/billing'
            isOpen={currentPath === '/settings/billing'}
            title={t({ id: 'js.Page.MainNav.billing.title', message: 'Billing' })}
          />
          <LinkLi
            href='/settings/plan'
            isOpen={currentPath === '/settings/plan'}
            title={t({ id: 'js.Page.MainNav.plan.title', message: 'Plan' })}
          />
        </ul>
      </LinkLi>
      <SetLocaleLinkLi />
      {user ? <LogoutLinkLi /> : null}
    </ul>
  )
}
BottomPaths.propTypes = {
  currentPath: PropTypes.string.isRequired,
  user: PropTypes.shape({
    stripeCustomerId: PropTypes.string // or null
  }) // or null
}
