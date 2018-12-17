import React from 'react'
import PropTypes from 'prop-types'

export default function PendingTab ({ name }) {
  return (
    <li className='pending'>
      <div className='tab-name'>
        {name}
      </div>
    </li>
  )
}
