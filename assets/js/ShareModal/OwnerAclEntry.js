import React from 'react'
import { Trans } from '@lingui/macro'

export default function OwnerAclEntry ({ email }) {
  return (
    <div className='acl-entry owner'>
      <div className='email'>{email}</div>
      <div className='role'><Trans id='js.ShareModal.OwnerAclEntry.owner'>Owner</Trans></div>
    </div>
  )
}
