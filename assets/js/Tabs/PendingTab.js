import React from 'react'
import PropTypes from 'prop-types'

export default function PendingTab ({ name }) {
  return (
    <li className='pending'>
      {name}
    </li>
  )
}
