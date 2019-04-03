import React from 'react'
import PropTypes from 'prop-types'
import { formatLocale as d3FormatLocale } from 'd3-format'
import EnUsLocale from 'd3-format/locale/en-US.json'

// Unfortunately, ReactDataGrid will send "new" values to "old" columns when
// switching to another version of a table that has the same column with a
// different type. So all formatters need to support all types. (We don't care
// about their output. though.)
const ReactDataGridValuePropType = PropTypes.oneOfType([
  PropTypes.string.isRequired,
  PropTypes.number.isRequired
])

export function TextCellFormatter ({value}) {
  if (value === null) {
    return <div className='cell-null cell-text' />
  }

  return <div className='cell-text' title={value}>{value}</div>
}

export function NumberCellFormatter (format) {
  const [ _, prefix, specifierString, suffix ] = /(.*?)\{:?(.*)\}(.*)/.exec(format)
  // format with the same locale as in Python -- _not_ the user's locale
  const locale = d3FormatLocale(EnUsLocale)
  const f = locale.format(specifierString)

  return ({value}) => {
    if (value === null) {
      return <div className='cell-null cell-number' />
    }

    return <div className='cell-number'>{prefix}{f(value)}{suffix}</div>
  }
}

const ZeroEndOfDate = /(?:(?:T00:00)?:00)?\.000Z$/
export function DatetimeCellFormatter ({value}) {
  // value is a string: -- ISO8601-formatted date
  if (value === null) {
    return <div className='cell-null cell-datetime' />
  }

  const date = new Date(value)
  if (isNaN(date)) {
    // A race! The input isn't a date because ReactDataGrid fed us "new"
    // data and we're the "old" formatter.
    return null // nobody will see it anyway
  }

  // Strip the end of the ISO string if it's all-zero. Restore the 'Z' at
  // the very end iff there's no time component. (The time component starts
  // with 'T'.)
  const isoText = date.toISOString()
  const text = isoText.replace(ZeroEndOfDate, (m) => m[0][0] === 'T' ? '' : 'Z')

  return <time className='cell-datetime' dateTime={isoText}>{text}</time>
}

const TypeToCellFormatter = {
  'text': () => TextCellFormatter,
  'datetime': () => DatetimeCellFormatter,
  'number': ({ format }) => NumberCellFormatter(format),
}

export function columnToCellFormatter (column) {
  return (TypeToCellFormatter[column.type] || TextCellFormatter)(column)
}
