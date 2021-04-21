import PropTypes from 'prop-types'
import NullCell from './NullCell'

const Formatters = {
  day: s => s,
  week: s => s,
  month: s => s.slice(0, 7),
  quarter: s => s.slice(0, 4) + ' ' + { '01': 'Q1', '04': 'Q2', '07': 'Q3', 10: 'Q4' }[s.slice(5, 7)],
  year: s => s.slice(0, 4)
}

export function makeDateCellComponent (unit) {
  const formatter = Formatters[unit] || (s => s)

  function DateCell (props) {
    const { value } = props

    if (value === null) {
      return <NullCell type='date' />
    }

    const text = formatter ? formatter(value) : value
    return <div className='cell-date'>{text}</div>
  }
  DateCell.propTypes = {
    value: PropTypes.string // ISO8601 date, or null
  }
  return DateCell
}
