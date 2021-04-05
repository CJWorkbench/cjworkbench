import { useMemo } from 'react'
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

function Price (props) {
  const { price, onClickSubscribe } = props

  const handleClickSubscribe = useMemo(
    () =>
      onClickSubscribe
        ? () => onClickSubscribe(price.stripePriceId)
        : null,
    [onClickSubscribe, price]
  )

  return (
    <div className='price'>
      <div className='amount' key={price.stripePriceId}>
        <StripeAmount
          amount={price.amount}
          currency={price.currency}
          interval={price.interval}
        />
      </div>
      {handleClickSubscribe
        ? (
          <Subscribe onClick={handleClickSubscribe} />
          )
        : null}
    </div>
  )
}
Price.propTypes = {
  price: PropTypes.shape({
    stripePriceId: PropTypes.string.isRequired,
    amount: PropTypes.number.isRequired,
    currency: PropTypes.string.isRequired,
    interval: PropTypes.oneOf(['month', 'year']).isRequired
  }).isRequired,
  onClickSubscribe: PropTypes.func // func(stripePriceId) => undefined, or null for no button
}

function ProductTh (props) {
  const { product, subscribed, onClickSubscribe, user } = props

  return (
    <th className={subscribed ? 'subscribed' : ''}>
      <div>
        <h2>{product.name}</h2>
        {product.prices.map(price => (
          <Price
            key={price.stripePriceId}
            price={price}
            user={user}
            onClickSubscribe={subscribed ? null : onClickSubscribe}
          />
        ))}
        {subscribed
          ? (
            <div className='current'>
              <Trans id='js.settings.Plan.PlanTable.current'>Current plan</Trans>
            </div>
            )
          : null}
        {user
          ? null
          : (
            <a href='/account/login/?next=%2Fsettings%2Fplan'>
              {product.prices.length
                ? (
                  <Trans id='js.settings.Plan.PlanTable.signInForFreePlan'>
                    Choose {product.name}
                  </Trans>
                  )
                : (
                  <Trans id='js.settings.Plan.PlanTable.signInToSubscribe'>
                    Choose {product.name}
                  </Trans>
                  )}
            </a>
            )}
      </div>
    </th>
  )
}
ProductTh.propTypes = {
  onClickSubscribe: PropTypes.func, // func(stripePriceId) => undefined, or null for no button
  product: PropTypes.shape({
    stripeProductId: PropTypes.string, // or null for free plan
    name: PropTypes.string.isRequired,
    prices: PropTypes.arrayOf(
      PropTypes.shape({
        amount: PropTypes.number.isRequired,
        currency: PropTypes.string.isRequired,
        interval: PropTypes.oneOf(['month', 'year']).isRequired
      }).isRequired
    ).isRequired
  }).isRequired,
  user: PropTypes.object, // or null if not signed in
  subscribed: PropTypes.bool.isRequired
}

export default function PlanTable (props) {
  const { products, onClickSubscribe, user } = props

  const activeStripeProductIds = user ? user.subscribedStripeProductIds : []

  return (
    <div className='plan-table'>
      <table>
        <thead>
          <tr>
            <th />
            {products.map(product => (
              <ProductTh
                key={product.stripeProductId}
                product={product}
                user={user}
                subscribed={
                  activeStripeProductIds.includes(product.stripeProductId) ||
                  Boolean(
                    activeStripeProductIds.length === 0 &&
                      product.prices.length === 0 &&
                      user
                  )
                }
                onClickSubscribe={onClickSubscribe}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>
              <h3>
                <Trans id='js.settings.Plan.PlanTable.maxFetchesPerDay.title'>
                  Automatic updates
                </Trans>
              </h3>
              <p>
                <Trans id='js.settings.Plan.PlanTable.maxFetchesPerDay.description'>
                  Per day
                </Trans>
              </p>
            </th>
            {products.map(product => (
              <td key={product.stripeProductId}>
                <div>
                  <Trans id='js.settings.Plan.PlanTable.maxFetchesPerDay.cell'>
                    {i18n.number(product.maxFetchesPerDay)} updates
                  </Trans>
                </div>
              </td>
            ))}
          </tr>
          <tr>
            <th>
              <h3>
                <Trans id='js.settings.Plan.PlanTable.canCreateSecretLink.title'>
                  Secret links
                </Trans>
              </h3>
              <p>
                <Trans id='js.settings.Plan.PlanTable.canCreateSecretLink.description'>
                  For sharing with non-Workbench users
                </Trans>
              </p>
            </th>
            {products.map(product => (
              <td key={product.stripeProductId}>
                <div>
                  {product.canCreateSecretLink ? '✔' : ''}
                </div>
              </td>
            ))}
          </tr>
          <tr>
            <th>
              <h3>
                <Trans id='js.settings.Plan.PlanTable.maxDeltaAgeInDays.title'>
                  Undo history
                </Trans>
              </h3>
            </th>
            {products.map(product => (
              <td key={product.stripeProductId}>
                <div className='bool'>{formatMaxDeltaAge(product.maxDeltaAgeInDays)}</div>
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
  products: PropTypes.arrayOf(
    PropTypes.shape({
      stripeProductId: PropTypes.string, // or null for free plan
      name: PropTypes.string.isRequired,
      maxFetchesPerDay: PropTypes.number.isRequired,
      maxDeltaAgeInDays: PropTypes.number.isRequired,
      canCreateSecretLink: PropTypes.bool.isRequired,
      prices: PropTypes.arrayOf(
        PropTypes.shape({
          stripePriceId: PropTypes.string.isRequired,
          amount: PropTypes.number.isRequired,
          currency: PropTypes.string.isRequired,
          interval: PropTypes.oneOf(['month', 'year']).isRequired
        }).isRequired
      ).isRequired
    }).isRequired
  ).isRequired,
  user: PropTypes.shape({
    subscribedStripeProductIds: PropTypes.arrayOf(PropTypes.string.isRequired)
      .isRequired
  }) // or null for anonymous
}
