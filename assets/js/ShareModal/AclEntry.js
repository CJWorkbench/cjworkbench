import React from 'react'
import PropTypes from 'prop-types'
import Role from './Role'

export default class AclEntry extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    email: PropTypes.string.isRequired,
    canEdit: PropTypes.bool.isRequired,
    updateAclEntry: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    deleteAclEntry: PropTypes.func.isRequired // func(email) => undefined
  }

  onChangeCanEdit = (canEdit) => {
    const { updateAclEntry, email } = this.props
    updateAclEntry(email, canEdit)
  }

  onClickDelete = () => {
    const { deleteAclEntry, email } = this.props
    deleteAclEntry(email)
  }

  render () {
    const { email, canEdit, isReadOnly } = this.props

    return (
      <div className='acl-entry'>
        <div className='email'>{email}</div>
        <Role canEdit={canEdit} isReadOnly={isReadOnly} onChange={this.onChangeCanEdit} />
        {isReadOnly ? null : (
          <button className='btn btn-danger delete' onClick={this.onClickDelete}>✖</button>
        )}
      </div>
    )
  }
}
