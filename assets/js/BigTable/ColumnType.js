import PropTypes from 'prop-types'
import { Trans } from '@lingui/react'

export default function ColumnType (props) {
  const { type, dateUnit } = props

  switch (type) {
    case 'date':
      switch (dateUnit) {
        case 'week':
          return <Trans id='js.table.ColumnHeader.types.date.week'>date – week</Trans>
        case 'month':
          return <Trans id='js.table.ColumnHeader.types.date.week'>date – month</Trans>
        case 'quarter':
          return <Trans id='js.table.ColumnHeader.types.date.week'>date – quarter</Trans>
        case 'year':
          return <Trans id='js.table.ColumnHeader.types.date.week'>date – year</Trans>
        default:
          return <Trans id='js.table.ColumnHeader.types.date.day'>date</Trans>
      }
    case 'text':
      return <Trans id='js.table.ColumnHeader.types.text'>text</Trans>
    case 'number':
      return <Trans id='js.table.ColumnHeader.types.number'>number</Trans>
    case 'timestamp':
      return <Trans id='js.table.ColumnHeader.types.timestamp'>timestamp</Trans>
  }
}
ColumnType.propTypes = {
  type: PropTypes.oneOf(['date', 'number', 'text', 'timestamp']).isRequired,
  dateUnit: PropTypes.oneOf(['day', 'week', 'month', 'quarter', 'year']) // or null
}
