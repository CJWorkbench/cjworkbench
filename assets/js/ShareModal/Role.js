import React from 'react'
import PropTypes from 'prop-types'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'

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
    const { canEdit } = this.props

    return (
      <UncontrolledDropdown>
        <DropdownToggle caret>
          {canEdit ? 'Can edit' : 'Can view'}
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem className='can-edit-false' active={!canEdit} onClick={this.unsetCanEdit}>Can view</DropdownItem>
          <DropdownItem className='can-edit-true' active={canEdit} onClick={this.setCanEdit}>Can edit</DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}
