import { formatLocale as d3FormatLocale } from 'd3-format'
import EnUsLocale from 'd3-format/locale/en-US.json'

// Unfortunately, ReactDataGrid will send "new" values to "old" columns when
// switching to another version of a table that has the same column with a
// different type. So all formatters need to support all types. (We don't care
// about their output. though.)

// Line breaks: https://www.unicode.org/reports/tr14/tr14-32.html#BK
const UnicodeWhitespace = /(?:\r\n|[\r\n\f\v\u0085\u2028\u2029])/g
const UnicodeWhitespaceReplacements = {
  '\r\n': '↵',
  '\r': '↵',
  '\n': '↵',
  '\u0085': '↵',
  '\u2028': '↵',
  '\u2029': '¶',
  '\f': '↡',
  '\v': '⭿'
}

export function TextCellFormatter ({ value }) {
  if (value === null) {
    return <div className='cell-null cell-text' />
  }

  value = String(value)
  // Make a one-line value: we'll style it with white-space: pre so the user
  // can see spaces.
  const oneLineValue = value.replace(
    UnicodeWhitespace,
    (x) => UnicodeWhitespaceReplacements[x]
  )

  return <div className='cell-text' title={value}>{oneLineValue}</div>
}

/**
 * Build { prefix, specifierString, suffix } from Python format string.
 *
 * format() is a function.
 */
function parseFormat (format) {
  try {
    const [, prefix, specifierString, suffix] = /(.*?)\{:?(.*)\}(.*)/.exec(format)
    return { prefix, suffix, specifierString }
  } catch (e) {
    if (e instanceof TypeError) {
      return { prefix: '', suffix: '', specifierString: ',' }
    }
  }
}

export function NumberCellFormatter (format) {
  let { prefix, suffix, specifierString } = parseFormat(format)
  // format with the same locale as in Python -- _not_ the user's locale
  const locale = d3FormatLocale(EnUsLocale)
  const d3Format = locale.format(specifierString)

  // Python/d3 allow a '%' format type which multiplies numbers and adds '%'.
  // We want the multiplication, but we want to render the '%' as a suffix so we
  // can style it.
  let f
  if (specifierString.endsWith('%')) {
    suffix = '%' + suffix
    f = (n) => d3Format(n).slice(0, -1)
  } else {
    f = d3Format
  }

  return ({ value }) => {
    if (value === null) {
      return <div className='cell-null cell-number' />
    }

    return (
      <div className='cell-number'>
        {prefix ? <span className='number-prefix'>{prefix}</span> : null}
        <span className='number-value'>{f(value)}</span>
        {suffix ? <span className='number-suffix'>{suffix}</span> : null}
      </div>
    )
  }
}

const ZeroEndOfDate = /(?:(?:T00:00)?:00)?\.000Z$/
export function TimestampCellFormatter ({ value }) {
  // value is a string: -- ISO8601-formatted date
  if (value === null) {
    return <div className='cell-null cell-timestamp' />
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

  return <time className='cell-timestamp' dateTime={isoText}>{text}</time>
}

const TypeToCellFormatter = {
  text: () => TextCellFormatter,
  timestamp: () => TimestampCellFormatter,
  number: ({ format }) => NumberCellFormatter(format)
}

export function columnToCellFormatter (column) {
  return (TypeToCellFormatter[column.type] || TextCellFormatter)(column)
}
