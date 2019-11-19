import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default class DateGranularity extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <select name=...>
    colname: PropTypes.string.isRequired,
    value: PropTypes.oneOf('STHDMQY'.split('')), // or null
    onChange: PropTypes.func.isRequired // func(colname, value) => undefined
  }

  handleChange = (ev) => {
    const { colname, onChange } = this.props
    onChange(colname, ev.target.value || null)
  }

  render () {
    const { isReadOnly, name, colname, value } = this.props

    // Mimic <MenuParam>'s HTML, but with string values. As of [2019-01-04],
    // <MenuParam> still only allows integer values, even though _every_ use
    // case warrants strings.

    return (
      <label className='date-granularity'>
        <h5><Trans id='js.params.Custom.Groups.DateGranularity.heading.title'>Granularity of “{colname}”</Trans></h5>
        <select
          className='custom-select'
          name={name}
          value={value || ''}
          onChange={this.handleChange}
          readOnly={isReadOnly}
        >
          <option value=''><Trans id='js.params.Custom.Groups.DateGranularity.asIs.option'>as is</Trans></option>
          <option value='S'><Trans id='js.params.Custom.Groups.DateGranularity.bySecond.option'>by second</Trans></option>
          <option value='T'><Trans id='js.params.Custom.Groups.DateGranularity.byMinute.option'>by minute</Trans></option>
          <option value='H'><Trans id='js.params.Custom.Groups.DateGranularity.byHour.option'>by hour</Trans></option>
          <option value='D'><Trans id='js.params.Custom.Groups.DateGranularity.byDay.option'>by day</Trans></option>
          <option value='M'><Trans id='js.params.Custom.Groups.DateGranularity.byMonth.option'>by month</Trans></option>
          <option value='Q'><Trans id='js.params.Custom.Groups.DateGranularity.byQuarter.option'>by quarter</Trans></option>
          <option value='Y'><Trans id='js.params.Custom.Groups.DateGranularity.byYear.option'>by year</Trans></option>
        </select>
      </label>
    )
  }
}
