import React from 'react'
import PropTypes from 'prop-types'
import TabName from './TabName'
import TabDropdown from './TabDropdown'

export default class Tab extends React.PureComponent {
  static propTypes = {
    id: PropTypes.number.isRequired,
    isSelected: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired,
    setName: PropTypes.func.isRequired, // func(tabId, name) => undefined
    destroy: PropTypes.func.isRequired, // func(tabId) => undefined
    select: PropTypes.func.isRequired, // func(tabId) => undefined
  }

  state = {
    isEditingTabName: false
  }

  get name () {
    return this.props.name || '…'

  }

  startEditingTabName = () => {
    this.setState({ isEditingTabName: true })
  }

  submitName = (name) => {
    const { setName, id } = this.props
    setName(id, name)
    this.setState({ isEditingTabName: false })
  }

  stopEditingTabName = () => {
    this.setState({ isEditingTabName: false })
  }

  destroy = () => {
    const { destroy, id } = this.props
    destroy(id)
  }

  onClickTab = () => {
    const { select, id, isSelected } = this.props
    if (isSelected) {
      this.startEditingTabName()
    } else {
      select(id)
    }
  }

  render () {
    const { isSelected, name, index } = this.props
    const { isEditingTabName } = this.state

    return (
      <li className={isSelected ? 'selected' : ''}>
        <TabName
          name={this.name}
          index={index}
          isEditing={isEditingTabName}
          onClick={this.onClickTab}
          onSubmitEdit={this.submitName}
          onCancelEdit={this.stopEditingTabName}
        />
        <TabDropdown
          onClickRename={this.startEditingTabName}
          onClickDelete={this.destroy}
        />
      </li>
    )
  }
}
