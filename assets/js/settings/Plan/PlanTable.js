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
  const { plan, active, onClickSubscribe } = props

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
        {active ? (
          <div className='current'>
            <Trans id='js.settings.Plan.PlanTable.current'>Current plan</Trans>
          </div>
        ) : null}
        {onClickSubscribe ? (
          <Subscribe onClick={onClickSubscribe} />
        ) : null}
      </div>
    </th>
  )
}
PlanTh.propTypes = {
  onClickSubscribe: PropTypes.func, // func() => undefined ... or null if can't subscribe
  plan: PropTypes.shape({
    name: PropTypes.string.isRequired,
    amount: PropTypes.number.isRequired,
    currency: PropTypes.string.isRequired
  }).isRequired,
  active: PropTypes.bool.isRequired
}

export default function PlanTable (props) {
  const { plans, activePlanIds, onClickSubscribe } = props

  return (
    <table className='plans'>
      <thead>
        <tr>
          <th />
          {plans.map(plan => (
            <PlanTh
              key={plan.stripePriceId}
              plan={plan}
              active={activePlanIds.includes(plan.stripePriceId) || (plan.stripePriceId === null && activePlanIds.length === 0)}
              onClickSubscribe={activePlanIds.length > 0 || plan.stripePriceId === null ? null : onClickSubscribe}
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
  )
}
PlanTable.propTypes = {
  onClickSubscribe: PropTypes.func.isRequired, // func() => undefined
  plans: PropTypes.arrayOf(
    PropTypes.shape({
    }).isRequired
  ).isRequired,
  activePlanIds: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired
}
