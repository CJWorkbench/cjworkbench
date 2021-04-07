import PropTypes from 'prop-types'
import NullCell from './NullCell'

const ZeroEndOfDate = /(?:(?:T00:00)?:00)?\.000Z$/

export default function TimestampCell (props) {
  const { value } = props

  if (value === null) {
    return <NullCell type='timestamp' />
  }

  // Strip the end of the ISO string if it's all-zero. Restore the 'Z' at
  // the very end iff there's no time component. (The time component starts
  // with 'T'.)
  const text = value.replace(ZeroEndOfDate, m => (m[0][0] === 'T' ? '' : 'Z'))

  return (
    <time className='cell-timestamp' dateTime={value}>
      {text}
    </time>
  )
}
TimestampCell.propTypes = {
  value: PropTypes.string // ISO8601-formatted date, or null
}
