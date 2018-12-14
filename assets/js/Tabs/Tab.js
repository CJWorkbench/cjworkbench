import React from 'react'
import PropTypes from 'prop-types'
import EditableTabName from './EditableTabName'

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

  render () {
    const { id, name, index, setName, select } = this.props
    const { isEditingTabName } = this.state

    return (
      <li>
        <div className='tab' onClick={select}>
          <EditableTabName
            value={this.name}
            isEditing={isEditingTabName}
            onClick={this.startEditingTabName}
            onSubmit={this.submitName}
            onCancel={this.cancelEditTabName}
          />
        </div>
      </li>
    )
  }
}
