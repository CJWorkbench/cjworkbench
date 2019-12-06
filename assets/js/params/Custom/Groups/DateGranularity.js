import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class DateGranularity extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <select name=...>
    colname: PropTypes.string.isRequired,
    value: PropTypes.oneOf('STHDMQY'.split('')), // or null
    onChange: PropTypes.func.isRequired, // func(colname, value) => undefined
    i18n: PropTypes.object
  }

  handleChange = (ev) => {
    const { colname, onChange } = this.props
    onChange(colname, ev.target.value || null)
  }

  render () {
    const { isReadOnly, name, colname, value, i18n } = this.props

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
          <option value=''>{i18n._(t('js.params.Custom.Groups.DateGranularity.asIs.option')`as is`)}</option>
          <option value='S'>{i18n._(t('js.params.Custom.Groups.DateGranularity.bySecond.option')`by second`)}</option>
          <option value='T'>{i18n._(t('js.params.Custom.Groups.DateGranularity.byMinute.option')`by minute`)}</option>
          <option value='H'>{i18n._(t('js.params.Custom.Groups.DateGranularity.byHour.option')`by hour`)}</option>
          <option value='D'>{i18n._(t('js.params.Custom.Groups.DateGranularity.byDay.option')`by day`)}</option>
          <option value='M'>{i18n._(t('js.params.Custom.Groups.DateGranularity.byMonth.option')`by month`)}</option>
          <option value='Q'>{i18n._(t('js.params.Custom.Groups.DateGranularity.byQuarter.option')`by quarter`)}</option>
          <option value='Y'>{i18n._(t('js.params.Custom.Groups.DateGranularity.byYear.option')`by year`)}</option>
        </select>
      </label>
    )
  }
}

export default withI18n()(DateGranularity)
