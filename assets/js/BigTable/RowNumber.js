import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'

export default function RowNumber ({ rowIndex }) {
  const s = i18n.number(rowIndex + 1)
  return <span data-n-chars={s.length}>{s}</span>
}
RowNumber.propTypes = {
  rowIndex: PropTypes.number.isRequired
}
