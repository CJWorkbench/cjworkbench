import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import { i18n } from '@lingui/core'
import Subscribe from './Subscribe'
import StripeAmount from '../StripeAmount'

function formatMaxDeltaAge (nDays) {
  const nMonths = Math.floor(nDays / 30)
  if (nMonths > 0) {
    return t({
      id: 'js.settings.Plan.PlanTable.maxDeltaAgeInDays.nMonths',
      message: '{nMonths, plural, one {# month} other {# months}}',
      values: { nMonths }
    })
  } else {
    return t({
      id: 'js.settings.Plan.PlanTable.maxDeltaAgeInDays.nDays',
      message: '{nDays, plural, one {# day} other {# days}}',
      values: { nDays }
    })
  }
}

function PlanTh (props) {
  const { plan, active, onClickSubscribe, user } = props

  return (
    <th className={active ? 'active' : ''}>
      <div>
        <h2>{plan.name}</h2>
        {plan.amount ? (
          <div className='amount'>
            <Trans id='js.settings.Plan.PlanTable.amount'>
              <strong><StripeAmount value={plan.amount} currency={plan.currency} /></strong>/month
            </Trans>
          </div>
        ) : null}
        {!user && !plan.amount ? (
          <a href='/account/login/?next=%2Fsettings%2Fplan'>
            <Trans id='js.settings.Plan.PlanTable.signInForFreePlan'>Choose {plan.name}</Trans>
          </a>
        ) : null}
        {active ? (
          <div className='current'>
            <Trans id='js.settings.Plan.PlanTable.current'>Current plan</Trans>
          </div>
        ) : null}
        {plan.amount && !active ? (
          user ? (
            <Subscribe onClick={onClickSubscribe} />
          ) : (
            <a href='/account/login/?next=%2Fsettings%2Fplan'>
              <Trans id='js.settings.Plan.PlanTable.signInToSubscribe'>Choose {plan.name}</Trans>
            </a>
          )
        ) : null}
      </div>
    </th>
  )
}
PlanTh.propTypes = {
  onClickSubscribe: PropTypes.func.isRequired, // func() => undefined
  plan: PropTypes.shape({
    name: PropTypes.string.isRequired,
    amount: PropTypes.number.isRequired,
    currency: PropTypes.string.isRequired
  }).isRequired,
  user: PropTypes.object, // or null if not signed in
  active: PropTypes.bool.isRequired
}

export default function PlanTable (props) {
  const { plans, onClickSubscribe, user } = props

  const activePlanIds = React.useMemo(
    () => user ? user.subscribedPlans.map(p => p.stripePriceId) : [],
    [user]
  )

  return (
    <div className='plan-table'>
      <table>
        <thead>
          <tr>
            <th />
            {plans.map(plan => (
              <PlanTh
                key={plan.stripePriceId}
                plan={plan}
                user={user}
                active={
                  activePlanIds.includes(plan.stripePriceId) ||
                  (activePlanIds.length === 0 && plan.amount === 0 && user)
                }
                onClickSubscribe={onClickSubscribe}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>
              <h3><Trans id='js.settings.Plan.PlanTable.maxFetchesPerDay.title'>Automatic updates</Trans></h3>
              <p><Trans id='js.settings.Plan.PlanTable.maxFetchesPerDay.description'>Per day</Trans></p>
            </th>
            {plans.map(plan => (
              <td key={plan.stripePriceId}>
                <div>
                  <Trans id='js.settings.Plan.PlanTable.maxFetchesPerDay.cell'>{i18n.number(plan.maxFetchesPerDay)} updates</Trans>
                </div>
              </td>
            ))}
          </tr>
          <tr>
            <th>
              <h3><Trans id='js.settings.Plan.PlanTable.maxDeltaAgeInDays.title'>Undo history</Trans></h3>
            </th>
            {plans.map(plan => (
              <td key={plan.stripePriceId}>
                <div>{formatMaxDeltaAge(plan.maxDeltaAgeInDays)}</div>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
PlanTable.propTypes = {
  onClickSubscribe: PropTypes.func.isRequired, // func() => undefined
  plans: PropTypes.arrayOf(
    PropTypes.shape({
    }).isRequired
  ).isRequired,
  user: PropTypes.shape({
    subscribedPlans: PropTypes.arrayOf(
      PropTypes.shape({
        stripePriceId: PropTypes.string.isRequired
      }).isRequired
    ).isRequired
  }) // or null for anonymous
}
