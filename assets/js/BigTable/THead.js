import React from 'react'
import PropTypes from 'prop-types'
import { columnDefinitionType } from './types'

const EmptyProps = {}

const THead = React.memo(function THead ({ columns }) {
  return (
    <thead>
      <tr>
        <th className='row-number' scope='col' />
        {columns.map(({ headerComponent: Header, headerProps = EmptyProps }, i) => (
          <th key={i} scope='col'>
            <Header {...headerProps} />
          </th>
        ))}
      </tr>
    </thead>
  )
})
THead.propTypes = {
  columns: PropTypes.arrayOf(columnDefinitionType).isRequired
}
export default THead
