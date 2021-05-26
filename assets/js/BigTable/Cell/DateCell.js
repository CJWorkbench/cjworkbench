import PropTypes from 'prop-types'
import NullCell from './NullCell'

const formatDay = s => s
const formatWeek = formatDay
const formatMonth = s => s.slice(0, 7)
const formatQuarter = s => s.slice(0, 4) + ' ' + { '01': 'Q1', '04': 'Q2', '07': 'Q3', 10: 'Q4' }[s.slice(5, 7)]
const formatYear = s => s.slice(0, 4)

function makeDateCellComponent (formatter) {
  const fn = ({ value }) => {
    if (value === null) {
      return <NullCell type='date' />
    }

    return <div className='cell-date'>{formatter(value)}</div>
  }
  fn.propTypes = {
    value: PropTypes.string // or null
  }
  return fn
}

const DateDayCell = makeDateCellComponent(formatDay)
DateDayCell.displayName = 'DateDayCell'
const DateWeekCell = makeDateCellComponent(formatWeek)
DateWeekCell.displayName = 'DateWeekCell'
const DateMonthCell = makeDateCellComponent(formatMonth)
DateMonthCell.displayName = 'DateMonthCell'
const DateQuarterCell = makeDateCellComponent(formatQuarter)
DateQuarterCell.displayName = 'DateQuarterCell'
const DateYearCell = makeDateCellComponent(formatYear)
DateYearCell.displayName = 'DateYearCell'

export function getDateCellComponent (unit) {
  return {
    day: DateDayCell,
    week: DateWeekCell,
    month: DateMonthCell,
    quarter: DateQuarterCell,
    year: DateYearCell
  }[unit]
}
