import React from 'react'
import PropTypes from 'prop-types'

export default function PendingTab ({ name }) {
  return (
    <li>
      <div className='tab tab-pending'>
        <div className='tab-name'>
          {name}
        </div>
      </div>
    </li>
  )
}
