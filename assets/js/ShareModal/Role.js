import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'

const ReadOnlyRole = ({ canEdit }) => (
  <p className="role">
    {canEdit ? 'Can edit' : 'Can view'}
  </p>
)

const EditableRole = ({ canEdit, setCanEdit, unsetCanEdit }) => (
  <UncontrolledDropdown>
    <DropdownToggle caret>
      {canEdit ? 'Can edit' : 'Can view'}
    </DropdownToggle>
    <DropdownMenu>
      <DropdownItem className='can-edit-false' active={!canEdit} onClick={unsetCanEdit}>Can view</DropdownItem>
      <DropdownItem className='can-edit-true' active={canEdit} onClick={setCanEdit}>Can edit</DropdownItem>
    </DropdownMenu>
  </UncontrolledDropdown>
)

export default class Role extends React.PureComponent {
  static propTypes = {
    canEdit: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(canEdit) => undefined
  }

  setCanEdit = () => {
    if (this.props.canEdit) return
    this.props.onChange(true)
  }

  unsetCanEdit = () => {
    if (!this.props.canEdit) return
    this.props.onChange(false)
  }

  render () {
    const { isReadOnly, canEdit } = this.props

    if (isReadOnly) {
      return <ReadOnlyRole canEdit={canEdit} />
    } else {
      return <EditableRole canEdit={canEdit} setCanEdit={this.setCanEdit} unsetCanEdit={this.unsetCanEdit} />
    }
  }
}
