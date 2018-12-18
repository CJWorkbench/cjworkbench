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
    dragging: PropTypes.shape({
      fromIndex: PropTypes.number.isRequired,
      toIndex: PropTypes.number.isRequired,
    }), // or null if not dragging
    onDragStart: PropTypes.func.isRequired, // func(index) => undefined
    onDragHoverIndex: PropTypes.func.isRequired, // func(index) => undefined
    onDragEnd: PropTypes.func.isRequired, // func() => undefined -- from source Tab after drop/cancel
    onDrop: PropTypes.func.isRequired, // func() => undefined -- from dest Tab after drop
    setName: PropTypes.func.isRequired, // func(tabId, name) => undefined
    destroy: PropTypes.func.isRequired, // func(tabId) => undefined
    select: PropTypes.func.isRequired, // func(tabId) => undefined
  }

  liRef = React.createRef()

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

  get isDragMode () {
    return this.props.dragging !== null
  }

  onDragStart = (ev) => {
    const { onDragStart, index, name } = this.props

    ev.dataTransfer.effectAllowed = 'move'
    ev.dataTransfer.setData('text/plain', name)
    ev.dataTransfer.setDragImage(ev.target, 0, 0)

    onDragStart(index)
  }

  onDragOver = (ev) => {
    if (!this.isDragMode) return // we aren't dragging a tab

    ev.preventDefault() // allow drop
  }

  onDragOver = (ev) => {
    if (!this.isDragMode) return // we aren't dragging a tab
    ev.preventDefault() // drop is ok

    const { onDragHoverIndex, index } = this.props

    const liRect = this.liRef.current.getBoundingClientRect()
    const x = ev.screenX

    const isLeft = x <= liRect.left + liRect.width / 2
    onDragHoverIndex(index + (isLeft ? 0 : 1))
  }

  onDragEnd = () => {
    if (!this.isDragMode) return // we aren't dragging a tab

    this.props.onDragEnd()
  }

  onDrop = (ev) => {
    if (!this.isDragMode) return // we aren't dragging a tab
    ev.preventDefault() // we want no browser defaults
    this.props.onDrop()
  }

  /**
   * 'dropping-left', 'dropping-right' or null
   */
  get droppingClassName () {
    if (!this.isDragMode) return null

    const { index, dragging } = this.props
    const { fromIndex, toIndex } = dragging

    if (fromIndex === toIndex || fromIndex + 1 === toIndex) return null

    if (index === toIndex) {
      return 'dropping-left' // drop is happening to the _left_ of this tab
    } else if (index === toIndex - 1) {
      return 'dropping-right' // drop is happening to the _right_ of this tab
    }

    return null
  }

  select = () => {
    const { id, select } = this.props
    select(id)
  }

  get isDragging () {
    const { dragging, index } = this.props
    return dragging && dragging.fromIndex === index
  }

  render () {
    const { isSelected, name, index } = this.props
    const { isEditingTabName } = this.state
    const droppingClassName = this.droppingClassName

    const classNames = []
    if (isSelected) classNames.push('selected')
    if (droppingClassName) classNames.push(droppingClassName)
    if (this.isDragging) classNames.push('dragging')

    return (
      <li
        ref={this.liRef}
        className={classNames.join(' ')}
      >
        <div
          className='tab'
          draggable
          onDragStart={this.onDragStart}
          onDragOver={this.onDragOver}
          onDragEnd={this.onDragEnd}
          onDrop={this.onDrop}
        >
          <TabName
            name={this.name}
            index={index}
            isEditing={isEditingTabName}
            onSelect={this.select}
            onRequestEdit={this.startEditingTabName}
            onSubmitEdit={this.submitName}
            onCancelEdit={this.stopEditingTabName}
          />
          <TabDropdown
            onClickRename={this.startEditingTabName}
            onClickDelete={this.destroy}
          />
        </div>
      </li>
    )
  }
}
