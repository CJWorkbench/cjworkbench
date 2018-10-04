import React from 'react'
import PropTypes from 'prop-types'
import AclEntry from './AclEntry'
import NewAclEntry from './NewAclEntry'
import OwnerAclEntry from './OwnerAclEntry'

export default class Acl extends React.PureComponent {
  static propTypes = {
    ownerEmail: PropTypes.string.isRequired,
    acl: PropTypes.arrayOf(PropTypes.shape({
      email: PropTypes.string.isRequired,
      canEdit: PropTypes.bool.isRequired
    }).isRequired).isRequired,
    onChange: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    onCreate: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    onClickDelete: PropTypes.func.isRequired, // func(email) => undefined
  }

  render () {
    const { acl, onChange, onCreate, onClickDelete, ownerEmail } = this.props

    return (
      <ul className='acl'>
        <li key='owner'>
          <OwnerAclEntry email={ownerEmail} />
        </li>
        {acl.map(entry => (
          <li key={entry.email}>
            <AclEntry {...entry} onChange={onChange} onClickDelete={onClickDelete} />
          </li>
        ))}
        <li key='new'>
          <NewAclEntry onCreate={onCreate} />
        </li>
      </ul>
    )
  }
}
