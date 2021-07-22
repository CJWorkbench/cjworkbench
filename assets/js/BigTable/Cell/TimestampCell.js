import PropTypes from 'prop-types'
import NullCell from './NullCell'

export default function TimestampCell (props) {
  const { value } = props

  if (value === null) {
    return <NullCell type='timestamp' />
  }

  // Assume input value is an ISO8601 string as compact as can be -- i.e., no
  // ":00" or ".000" when they aren't needed.
  // HTML5 time *requires* "HH:MM", whereas RFC3339 allows simply "HH". Add
  // the :00 where it's needed.
  const htmlValue = value.replace(/(T\d\d)Z/, '$1:00Z')

  // ISO8601 datetime always has a time component. Nix it if it's zero.
  const textValue = value.replace(/T00(?::00(?::00)?(?:\.0+)?)?Z/, '')

  return (
    <time className='cell-timestamp' dateTime={htmlValue}>
      {textValue}
    </time>
  )
}
TimestampCell.propTypes = {
  value: PropTypes.string // ISO8601-formatted date, or null
}
