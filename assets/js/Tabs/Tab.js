import React from 'react'
import PropTypes from 'prop-types'
import EditableTabName from './EditableTabName'
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
    return this.props.name || `Tab ${this.props.index}`
  }

  startEditingTabName = () => {
    this.setState({ isEditingTabName: true })
  }

  submitName = (name) => {
    const { setName, id } = this.props
    setName(id, name)
    this.setState({ isEditingTabName: false })
  }

  cancelEditTabName = () => {
    this.setState({ isEditingTabName: false })
  }

  destroy = () => {
    const { destroy, id } = this.props
    destroy(id)
  }

  onClickTab = () => {
    const { select, id } = this.props
    select(id)
  }

  render () {
    const { id, isSelected, name, index, setName } = this.props
    const { isEditingTabName } = this.state

    return (
      <li className={isSelected ? 'selected' : ''}>
        <EditableTabName
          value={this.name}
          isEditing={isEditingTabName}
          onClick={this.onClickTab}
          onSubmit={this.submitName}
          onCancel={this.cancelEditTabName}
        />
        <TabDropdown
          onClickRename={this.startEditingTabName}
          onClickDelete={this.destroy}
        />
      </li>
    )
  }
}
