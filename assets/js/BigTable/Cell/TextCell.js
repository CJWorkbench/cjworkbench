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

const ValidSchemes = /^https?:\/\/[^/]/
const UrlCodePointOrPercentEscape = "(?:[-!$&'()*+,./:;=?@_~0-9a-zA-Z\u{00a0}-\u{10fffd}]|%[0-9a-fA-F]{2})"
const AllUrlCodePointsOrPercentEscapes = new RegExp(`^${UrlCodePointOrPercentEscape}*(?:#${UrlCodePointOrPercentEscape}*)?$`, 'u')

function parseValidUrl (s) {
  // https://url.spec.whatwg.org/#concept-basic-url-parser
  // The spec talks of "validation error", but `URL()` does not expose
  // validation errors anywhere! (It recovers from them). So our algorithm
  // uses URL() for the "hard" parts ... and it returns false if it sees
  // some validation errors.

  if (!ValidSchemes.test(s)) {
    // avoid "url is special" everywhere
    // avoid "file" logic everywhere
    //
    // The regex also bans "https:///", because
    // https://url.spec.whatwg.org/#example-url-parsing says it's invalid,
    // though [adamhooper, 2021-05-27] I can't find the portion of the spec
    // that explains why it's invalid.
    return null
  }

  if (!AllUrlCodePointsOrPercentEscapes.test(s)) {
    // 1.2. If input contains any leading or trailing C0 control or space, validation error.
    // 1. If input contains any ASCII tab or newline, validation error.
    // path state: URL code point or invalid % => validation error
    // query state: URL code point or invalid % => validation error
    // fragment state: URL code point or invalid % => validation error
    return null
  }

  try {
    const url = new URL(s)
    return url.href
  } catch (e) {
    return null
  }
}

export default function TextCell (props) {
  const { value } = props
  if (value === null) {
    return <NullCell type='text' />
  }

  const href = parseValidUrl(value)
  if (href !== null) {
    return (
      <a
        className='cell-text'
        target='_blank'
        rel='noopener noreferrer'
        href={href}
      >
        {value}
      </a>
    )
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
