import React from 'react'
import PropTypes from 'prop-types'
import { NumberFormat } from '@lingui/react'

function RowNumberSpan ({ translation }) {
  return <span data-n-chars={translation.length}>{translation}</span>
}

export default function RowNumber ({ rowIndex }) {
  return <NumberFormat value={rowIndex + 1} render={RowNumberSpan} />
}
RowNumber.propTypes = {
  rowIndex: PropTypes.number.isRequired
}
