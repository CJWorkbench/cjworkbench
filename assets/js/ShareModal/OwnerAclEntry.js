import React from 'react'

export default function OwnerAclEntry ({ email }) {
  return (
    <div className='acl-entry owner'>
      <div className='email'>{email}</div>
      <div className='role'>Owner</div>
    </div>
  )
}
