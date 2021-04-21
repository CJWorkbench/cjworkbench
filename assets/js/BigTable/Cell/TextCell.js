import PropTypes from 'prop-types'
import NullCell from './NullCell'

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

export default function TextCell (props) {
  const { value } = props
  if (value === null) {
    return <NullCell type='text' />
  }

  // Make a one-line value: we'll style it with white-space: pre so the user
  // can see spaces.
  const oneLineValue = value.replace(
    UnicodeWhitespace,
    x => UnicodeWhitespaceReplacements[x]
  )

  return <div className='cell-text' title={value}>{oneLineValue}</div>
}
TextCell.propTypes = {
  value: PropTypes.string // or null
}
