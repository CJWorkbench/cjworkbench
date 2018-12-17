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

  onClickTab = () => {
    const { select, id, isSelected } = this.props
    if (isSelected) {
      this.startEditingTabName()
    } else {
      select(id)
    }
  }

  get isDragMode () {
    return this.props.dragging !== null
  }

  onDragStart = (ev) => {
    const { onDragStart, index, name } = this.props
    onDragStart(index)

    ev.dataTransfer.setData('text/plain', name)
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
   * 'nudge-left', 'nudge-right' or null
   */
  get nudgeClassName () {
    if (!this.isDragMode) return null

    const { index, dragging } = this.props
    const { fromIndex, toIndex } = dragging

    if (fromIndex === toIndex || fromIndex + 1 === toIndex) return null

    const draggingRight = toIndex > fromIndex

    if (draggingRight) {
      if (index <= fromIndex) return null // Don't nudge anything left of element being dragged
      return index < toIndex ? 'nudge-left' : 'nudge-right'
    } else { // dragging left
      if (index >= fromIndex) return null // Don't nudge anything right of element being dragged
      return index < toIndex ? 'nudge-left' : 'nudge-right'
    }
  }

  get isDragging () {
    const { dragging, index } = this.props
    return dragging && dragging.fromIndex === index
  }

  render () {
    const { isSelected, name, index } = this.props
    const { isEditingTabName } = this.state
    const nudgeClassName = this.nudgeClassName

    const classNames = []
    if (isSelected) classNames.push('selected')
    if (nudgeClassName) classNames.push(nudgeClassName)
    if (this.isDragging) classNames.push('dragging')

    return (
      <li
        ref={this.liRef}
        className={classNames.join(' ')}
        draggable
        onDragStart={this.onDragStart}
        onDragOver={this.onDragOver}
        onDragEnd={this.onDragEnd}
        onDrop={this.onDrop}
      >
        <div className='tab'>
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
        </div>
      </li>
    )
  }
}
