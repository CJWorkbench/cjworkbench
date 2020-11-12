import React from 'react'
import PropTypes from 'prop-types'
import { columnDefinitionType } from './types'

const ColGroup = React.memo(function ColGroup ({ columns }) {
  return (
    <colgroup>
      <col className='row-number' />
      {columns.map(({ width }, i) => (
        <col key={i} style={{ width: `${width}px` }} />
      ))}
    </colgroup>
  )
})
ColGroup.propTypes = {
  columns: PropTypes.arrayOf(columnDefinitionType).isRequired
}
export default ColGroup
