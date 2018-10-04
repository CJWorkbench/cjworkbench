import React from 'react'
import PropTypes from 'prop-types'
import Role from './Role'

export default class AclEntry extends React.PureComponent {
  static propTypes = {
    email: PropTypes.string.isRequired,
    canEdit: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    onClickDelete: PropTypes.func.isRequired // func(email) => undefined
  }

  onChangeCanEdit = (canEdit) => {
    const { onChange, email } = this.props
    onChange(email, canEdit)
  }

  onClickDelete = () => {
    const { onClickDelete, email } = this.props
    onClickDelete(email)
  }

  render () {
    const { email, canEdit } = this.props

    return (
      <div className='acl-entry'>
        <div className='email'>{email}</div>
        <Role canEdit={canEdit} onChange={this.onChangeCanEdit} />
        <button className='btn btn-danger delete' onClick={this.onClickDelete}>✖</button>
      </div>
    )
  }
}
