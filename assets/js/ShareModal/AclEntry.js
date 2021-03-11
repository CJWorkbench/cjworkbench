import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import Role from './Role'

export default class AclEntry extends PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    email: PropTypes.string.isRequired,
    role: PropTypes.oneOf(['editor', 'viewer', 'report-viewer']).isRequired,
    updateAclEntry: PropTypes.func.isRequired, // func(email, role) => undefined
    deleteAclEntry: PropTypes.func.isRequired // func(email) => undefined
  }

  handleChangeRole = role => {
    const { updateAclEntry, email } = this.props
    updateAclEntry(email, role)
  }

  handleClickDelete = () => {
    const { deleteAclEntry, email } = this.props
    deleteAclEntry(email)
  }

  render () {
    const { email, role, isReadOnly } = this.props

    return (
      <div className='acl-entry'>
        <div className='email'>{email}</div>
        <Role
          role={role}
          isReadOnly={isReadOnly}
          onChange={this.handleChangeRole}
        />
        {isReadOnly
          ? null
          : <button className='btn btn-danger delete' onClick={this.handleClickDelete}>✖</button>}
      </div>
    )
  }
}
