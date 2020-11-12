import React from 'react'
import PropTypes from 'prop-types'
import { columnDefinitionType } from './types'

const THead = React.memo(function THead ({ columns }) {
  return (
    <thead>
      <tr>
        <th className='row-number' scope='col' />
        {columns.map(({ headerComponent: Header }, i) => (
          <th key={i} scope='col'><Header /></th>
        ))}
      </tr>
    </thead>
  )
})
THead.propTypes = {
  columns: PropTypes.arrayOf(columnDefinitionType).isRequired
}
export default THead
