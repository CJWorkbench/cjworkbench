import React from 'react'
import PropTypes from 'prop-types'
import TabDropdown from './TabDropdown'

export default class Tab extends React.PureComponent {
  static propTypes = {
    slug: PropTypes.string.isRequired,
    isPending: PropTypes.bool, // or undefined
    isReadOnly: PropTypes.bool.isRequired,
    isSelected: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired,
    dragging: PropTypes.shape({
      fromIndex: PropTypes.number.isRequired,
      toIndex: PropTypes.number.isRequired
    }), // or null if not dragging
    onDragStart: PropTypes.func.isRequired, // func(index) => undefined
    onDragHoverIndex: PropTypes.func.isRequired, // func(index) => undefined
    onDragEnd: PropTypes.func.isRequired, // func() => undefined -- from source Tab after drop/cancel
    onDrop: PropTypes.func.isRequired, // func() => undefined -- from dest Tab after drop
    setName: PropTypes.func.isRequired, // func(slug, name) => undefined
    destroy: PropTypes.func.isRequired, // func(slug) => undefined
    duplicate: PropTypes.func.isRequired, // func(slug) => undefined
    select: PropTypes.func.isRequired // func(slug) => undefined
  }

  state = {
    name: null
  }

  inputRef = React.createRef()

  liRef = React.createRef()

  handleClickRename = () => {
    if (this.props.isReadOnly) return

    this.inputRef.current.focus()
    this.inputRef.current.select()
  }

  handleNameChange = (ev) => {
    this.setState({ name: ev.target.value })
  }

  handleNameKeyDown = (ev) => {
    switch (ev.key) {
      case 'Enter':
        this.props.setName(this.props.slug, this.state.name)
        this.setState({ name: null }) // for handleNameBlur()
        this.inputRef.current.blur()
        return
      case 'Escape':
        this.setState({ name: null }) // for handleNameBlur()
        this.inputRef.current.blur()
    }
  }

  handleNameBlur = () => {
    // handleKeyDown may have set value=null. If it did, we'll only detect that
    // within the setState() _callback_.
    this.setState(({ name }) => {
      if (name === null) {
        // handleKeyDown already handled this (or there was no edit)
      } else {
        this.props.setName(this.props.slug, name)
      }
    })
  }

  handleClickDelete = () => {
    const { destroy, slug } = this.props
    destroy(slug)
  }

  handleClickDuplicate = () => {
    const { duplicate, slug } = this.props
    duplicate(slug)
  }

  get isDragMode () {
    return this.props.dragging !== null
  }

  handleDragStart = (ev) => {
    const { isReadOnly, isSelected, onDragStart, index, name } = this.props
    if (isReadOnly) return

    ev.dataTransfer.effectAllowed = 'move'
    ev.dataTransfer.setData('text/plain', name)
    ev.dataTransfer.setDragImage(ev.currentTarget, 0, 0)

    // Styling is much easier if you can only move the selected element.
    if (!isSelected) this.select()

    // We disable the <input>'s _normal_ text-editing drag-and-drop
    // functionality (e.g., double-click a word, drag it elsewhere): it's
    // just too confusing to keep it running, especially across multiple
    // browsers. To be extra-clear, blur the input.
    this.inputRef.current.blur()

    onDragStart(index)
  }

  handleDragOver = (ev) => {
    if (!this.isDragMode) return // we aren't dragging a tab
    ev.preventDefault() // drop is ok

    const { onDragHoverIndex, index } = this.props

    const liRect = this.liRef.current.getBoundingClientRect()
    const x = ev.screenX

    const isLeft = x <= liRect.left + liRect.width / 2
    onDragHoverIndex(index + (isLeft ? 0 : 1))
  }

  handleDragEnd = () => {
    if (!this.isDragMode) return // we aren't dragging a tab

    this.props.onDragEnd()
  }

  handleDrop = (ev) => {
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

  handleClick = () => {
    const { slug, select, isPending } = this.props

    if (isPending) {
      // Don't allow selecting the tab yet. It _would_ work, but _other_ parts
      // of the client side will break because of it. For instance, we can't
      // add a module to pending tabs.
      //
      // TODO nix "pendingTabs" and build a more comprehensive store. If the
      // store queues uncommitted actions in a separate place from the current
      // state, we can nix this if-clause: the user won't care whether a tab
      // is pending.
      return
    }

    select(slug)
  }

  get isDragging () {
    const { dragging, index } = this.props
    return dragging && dragging.fromIndex === index
  }

  render () {
    const { isPending, isReadOnly, isSelected } = this.props
    const droppingClassName = this.droppingClassName
    const name = this.state.name === null ? this.props.name : this.state.name

    const classNames = []
    if (isPending) classNames.push('pending')
    if (isSelected) classNames.push('selected')
    if (droppingClassName) classNames.push(droppingClassName)
    if (this.isDragging) classNames.push('dragging')

    /*
     * Two equivalent representations of the same value:
     *
     * <span>: the text, not editable, used by CSS to compute size
     * <input>: what the user sees
     */
    return (
      <li
        ref={this.liRef}
        className={classNames.join(' ')}
      >
        <div
          className='tab'
          draggable={!isReadOnly}
          onClick={this.handleClick}
          onDragStart={this.handleDragStart}
          onDragOver={this.handleDragOver}
          onDragEnd={this.handleDragEnd}
          onDrop={this.handleDrop}
        >
          <span className='size-calculator'>{name}</span>
          <input
            name='tab-name'
            placeholder='…'
            ref={this.inputRef}
            value={name}
            disabled={isReadOnly || !isSelected}
            onChange={this.handleNameChange}
            onKeyDown={this.handleNameKeyDown}
            onBlur={this.handleNameBlur}
          />
          <TabDropdown
            onClickRename={this.handleClickRename}
            onClickDelete={this.handleClickDelete}
            onClickDuplicate={this.handleClickDuplicate}
          />
        </div>
      </li>
    )
  }
}
