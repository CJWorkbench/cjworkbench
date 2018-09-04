import React from 'react'
import PropTypes from 'prop-types'

// Custom Formatter component, to render row number in a different style
export class RowIndexFormatter extends React.PureComponent {
  static propTypes = {
    value: PropTypes.number.isRequired
  }

  render () {
    const text = String(this.props.value) // no commas -- horizontal space is at a premium

    return <div className={`row-number row-number-${text.length}`}>{text}</div>
  }
}

// Unfortunately, ReactDataGrid will send "new" values to "old" columns when
// switching to another version of a table that has the same column with a
// different type. So all formatters need to support all types. (We don't care
// about their output. though.)
const ReactDataGridValuePropType = PropTypes.oneOfType([
  PropTypes.string.isRequired,
  PropTypes.number.isRequired
])

class AbstractCellFormatter extends React.PureComponent {
  render () {
    const value = this.props.value
    if (value === null) {
      return <div className='cell-null'>{'null'}</div>
    }

    return this.renderNonNull()
  }
}

export class TextCellFormatter extends AbstractCellFormatter {
  static propTypes = {
    value: ReactDataGridValuePropType // string
  }

  renderNonNull () {
    return <div className='cell-text'>{this.props.value}</div>
  }
}

const numberFormat = new Intl.NumberFormat()
export class NumberCellFormatter extends AbstractCellFormatter {
  static propTypes = {
    value: ReactDataGridValuePropType // number
  }

  renderNonNull () {
    return <div className='cell-number'>{numberFormat.format(this.props.value)}</div>
  }
}

const ZeroEndOfDate = /(?:(?:T00:00)?:00)?\.000Z$/
export class DatetimeCellFormatter extends AbstractCellFormatter {
  static propTypes = {
    value: ReactDataGridValuePropType // string: -- ISO8601-formatted date
  }

  renderNonNull () {
    const value = this.props.value
    const date = new Date(value)

    if (isNaN(date)) {
      // A race! The input isn't a date because ReactDataGrid fed us "new"
      // data and we're the "old" formatter.
      return null // nobody will see it anyway
    }

    // Strip the end of the ISO string if it's all-zero. Restore the 'Z' at
    // the very end iff there's no time component. (The time component starts
    // with 'T'.)
    const text = date.toISOString()
      .replace(ZeroEndOfDate, (m) => m[0][0] === 'T' ? '' : 'Z')

    return <div className='cell-datetime'>{text}</div>
  }
}

const TypeToCellFormatter = {
  'text': TextCellFormatter,
  'datetime': DatetimeCellFormatter,
  'number': NumberCellFormatter
}

export function typeToCellFormatter (type) {
  return TypeToCellFormatter[type] || TextCellFormatter
}
