import React from 'react'
import PropTypes from 'prop-types'
import OAuthConnect from './OAuthConnect'

const Components = {
  google_credentials: OAuthConnect,
  twitter_credentials: OAuthConnect
}

const ComponentNotFound = ({ name }) => (
  <p className='error'>Secret type {name} not handled</p>
)

export default function Secret ({ value, name, deleteSecret, startCreateSecret }) {
  const secretName = value ? (value.name || null) : null

  return (
    <OAuthConnect
      paramIdName={name}
      startCreateSecret={startCreateSecret}
      deleteSecret={deleteSecret}
      secretName={secretName}
    />
  )
}
