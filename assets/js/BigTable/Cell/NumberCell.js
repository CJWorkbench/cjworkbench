import PropTypes from 'prop-types'
import { formatLocale as d3FormatLocale } from 'd3-format'
import NullCell from './NullCell'

const EnUsLocale = {
  // d3-format/locale/en-US.json
  decimal: '.',
  thousands: ',',
  grouping: [3],
  currency: ['$', '']
}

/**
 * Build { prefix, specifierString, suffix } from Python format string.
 *
 * format() is a function.
 */
function parseFormat (format) {
  try {
    const [, prefix, specifierString, suffix] = /(.*?)\{:?(.*)\}(.*)/.exec(
      format
    )
    return { prefix, suffix, specifierString }
  } catch (e) {
    if (e instanceof TypeError) {
      return { prefix: '', suffix: '', specifierString: ',' }
    }
  }
}

// format with the same locale as in Python -- _not_ the user's locale
const d3Locale = d3FormatLocale(EnUsLocale)

export function makeNumberCellComponent (format) {
  let { prefix, suffix, specifierString } = parseFormat(format)
  const d3Format = d3Locale.format(specifierString)

  // Python/d3 allow a '%' format type which multiplies numbers and adds '%'.
  // We want the multiplication, but we want to render the '%' as a suffix so we
  // can style it.
  let f
  if (specifierString.endsWith('%')) {
    suffix = '%' + suffix
    f = n => d3Format(n).slice(0, -1)
  } else {
    f = d3Format
  }

  function NumberCell (props) {
    const { value } = props

    if (value === null) {
      return <NullCell type='number' />
    }

    return (
      <div className='cell-number'>
        {prefix ? <span className='number-prefix'>{prefix}</span> : null}
        <span className='number-value'>{f(value)}</span>
        {suffix ? <span className='number-suffix'>{suffix}</span> : null}
      </div>
    )
  }
  NumberCell.propTypes = {
    value: PropTypes.number // or null
  }
  return NumberCell
}
