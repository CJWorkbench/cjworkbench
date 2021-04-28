import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'

export default function DateGranularity (props) {
  const { name, colname, value } = props

  // Mimic <MenuParam>'s HTML, but with string values. As of [2019-01-04],
  // <MenuParam> still only allows integer values, even though _every_ use
  // case warrants strings.

  return (
    <label className='date-granularity'>
      <h5>
        <Trans id='js.params.Custom.Groups.DateGranularity.heading.title'>
          Granularity of “{colname}”
        </Trans>
      </h5>
      <select
        className='custom-select'
        name={name}
        value={value || ''}
        disabled
      >
        <option value=''>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.asIs.option',
            message: 'as is'
          })}
        </option>
        <option value='S'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.bySecond.option',
            message: 'by second'
          })}
        </option>
        <option value='T'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.byMinute.option',
            message: 'by minute'
          })}
        </option>
        <option value='H'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.byHour.option',
            message: 'by hour'
          })}
        </option>
        <option value='D'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.byDay.option',
            message: 'by day'
          })}
        </option>
        <option value='W'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.byWeek.option',
            message: 'by week'
          })}
        </option>
        <option value='M'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.byMonth.option',
            message: 'by month'
          })}
        </option>
        <option value='Q'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.byQuarter.option',
            message: 'by quarter'
          })}
        </option>
        <option value='Y'>
          {t({
            id: 'js.params.Custom.Groups.DateGranularity.byYear.option',
            message: 'by year'
          })}
        </option>
      </select>
      {value === 'W'
        ? (
          <p>
            <Trans id='js.params.Custom.Groups.DateGranularity.byWeek.weekStartsMonday'>
              Weeks begin Monday at midnight UTC.
            </Trans>
          </p>
          )
        : null}
    </label>
  )
}
DateGranularity.propTypes = {
  name: PropTypes.string.isRequired, // <select name=...>
  colname: PropTypes.string.isRequired,
  value: PropTypes.oneOf('STHDWMQY'.split('')) // or null
}
