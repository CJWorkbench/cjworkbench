import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import LinkLi from './LinkLi'
import SetLocaleLinkLi from './SetLocaleLinkLi'
import LogoutLinkLi from './LogoutLinkLi'

function LoginLinkLi (props) {
  const { nextPath } = props
  return (
    <LinkLi
      href={`/account/login/?next=${encodeURIComponent(nextPath)}`}
      isOpen={false}
      title={t({ id: 'js.Page.MainNav.signIn.title', message: 'Sign in' })}
    />
  )
}

function BillingPaths (props) {
  const { currentPath, user = null } = props
  return (
    <>
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
    </>
  )
}

function LoggedInUserPaths (props) {
  const { currentPath, user } = props

  return (
    <>
      <h3 className='display-name'>{user.display_name}</h3>
      <ul>
        <BillingPaths currentPath={currentPath} user={user} />
        <SetLocaleLinkLi />
        <LogoutLinkLi nextPath={currentPath} />
      </ul>
    </>
  )
}

function AnonymousUserPaths (props) {
  const { currentPath } = props

  return (
    <ul>
      <BillingPaths currentPath={currentPath} user={null} />
      <SetLocaleLinkLi />
      <LoginLinkLi nextPath={currentPath} />
    </ul>
  )
}

export default function UserPaths (props) {
  const { currentPath, user } = props

  return (
    <div className='user-paths'>
      {user ? (
        <LoggedInUserPaths currentPath={currentPath} user={user} />
      ) : (
        <AnonymousUserPaths currentPath={currentPath} />
      )}
    </div>
  )
}
UserPaths.propTypes = {
  currentPath: PropTypes.string.isRequired,
  user: PropTypes.shape({
    display_name: PropTypes.string.isRequired,
    stripeCustomerId: PropTypes.string // or null
  }) // or null
}
