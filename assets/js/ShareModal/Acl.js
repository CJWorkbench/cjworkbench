import React from 'react'
import PropTypes from 'prop-types'
import AclEntry from './AclEntry'
import NewAclEntry from './NewAclEntry'
import OwnerAclEntry from './OwnerAclEntry'

export default class Acl extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired, // are we owner? otherwise ACL is read-only
    ownerEmail: PropTypes.string.isRequired,
    acl: PropTypes.arrayOf(PropTypes.shape({
      email: PropTypes.string.isRequired,
      canEdit: PropTypes.bool.isRequired
    }).isRequired).isRequired,
    updateAclEntry: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    deleteAclEntry: PropTypes.func.isRequired // func(email) => undefined
  }

  render () {
    const { acl, isReadOnly, updateAclEntry, deleteAclEntry, ownerEmail } = this.props

    return (
      <ul className='acl'>
        <li key='owner'>
          <OwnerAclEntry email={ownerEmail} />
        </li>
        {acl.map(entry => (
          <li key={entry.email}>
            <AclEntry {...entry} isReadOnly={isReadOnly} updateAclEntry={updateAclEntry} deleteAclEntry={deleteAclEntry} />
          </li>
        ))}
        {isReadOnly ? null : (
          <li key='new'>
            <NewAclEntry ownerEmail={ownerEmail} updateAclEntry={updateAclEntry} />
          </li>
        )}
      </ul>
    )
  }
}
