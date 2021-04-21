import PropTypes from 'prop-types'
import { t } from '@lingui/macro'

/**
 * Render an empty cell with className="cell-null" and data-text.
 *
 * The text is an attribute, not content, so copy/paste won't copy it.
 */
export default function NullCell (props) {
  const { type } = props
  const label = t({ id: 'js.BigTable.Cell.null', message: 'null' })
  return <div className={`cell-${type} cell-null`} data-text={label} />
}
NullCell.propTypes = {
  type: PropTypes.oneOf(['text', 'number', 'date', 'timestamp']).isRequired
}
