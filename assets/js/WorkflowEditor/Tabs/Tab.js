import React from 'react'
import PropTypes from 'prop-types'
import TabDropdown from './TabDropdown'

function EditableTabName (props) {
  const {
    inputRef,
    isReadOnly,
    placeholder,
    slug,
    value,
    onSubmit
  } = props

  const ignoreBlur = React.useRef(false)

  const [newValue, setNewValue] = React.useState(null)

  const submitIfChanged = () => {
    if (newValue !== null && newValue !== '' && newValue !== value) {
      onSubmit(slug, newValue) // caller's <EditableTabName key> will change, unmounting us
    }
  }

  const handleChange = React.useCallback(ev => { setNewValue(ev.target.value) }, [setNewValue])

  const handleBlur = () => {
    if (!ignoreBlur.current) {
      submitIfChanged()
    }
  }

  const blurWithoutEventHandler = () => {
    ignoreBlur.current = true
    inputRef.current.blur()
    ignoreBlur.current = false
  }

  const handleKeyDown = ev => {
    switch (ev.key) {
      case 'Enter':
        submitIfChanged()
        blurWithoutEventHandler()
        break
      case 'Escape':
        setNewValue(null)
        blurWithoutEventHandler()
        break
    }
  }

  const editedValue = newValue === null ? value : newValue

  return (
    <div className='editable-tab-name'>
      <span className='invisible-size-setter'>{editedValue || placeholder}</span>
      <input
        name='tab-name'
        placeholder={placeholder}
        ref={inputRef}
        value={editedValue}
        disabled={isReadOnly}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
      />
    </div>
  )
}

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

  inputRef = React.createRef()
  liRef = React.createRef()

  handleClickDelete = () => {
    const { destroy, slug } = this.props
    destroy(slug)
  }

  handleClickDuplicate = () => {
    const { duplicate, slug } = this.props
    duplicate(slug)
  }

  handleClickRename = () => {
    if (this.props.isReadOnly) return

    this.inputRef.current.focus()
    this.inputRef.current.select()
  }

  get isDragMode () {
    return this.props.dragging !== null
  }

  handleDragStart = ev => {
    const { isReadOnly, onDragStart, index, name } = this.props
    if (isReadOnly) return

    ev.dataTransfer.effectAllowed = 'move'
    ev.dataTransfer.setData('text/plain', name)
    ev.dataTransfer.setDragImage(ev.currentTarget, 0, 0)

    // We disable the <input>'s _normal_ text-editing drag-and-drop
    // functionality (e.g., double-click a word, drag it elsewhere): it's
    // just too confusing to keep it running, especially across multiple
    // browsers. To be extra-clear, blur the input.
    this.inputRef.current.blur()

    onDragStart(index)
  }

  handleDragOver = ev => {
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

  handleDrop = ev => {
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
    const { isPending, isReadOnly, isSelected, slug, name, setName } = this.props
    const droppingClassName = this.droppingClassName

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
      <li ref={this.liRef} className={classNames.join(' ')}>
        <div
          className='tab'
          draggable={!isReadOnly}
          onClick={this.handleClick}
          onDragStart={this.handleDragStart}
          onDragOver={this.handleDragOver}
          onDragEnd={this.handleDragEnd}
          onDrop={this.handleDrop}
        >
          <EditableTabName
            placeholder='…'
            slug={slug}
            key={name /* reset when name changes */}
            inputRef={this.inputRef}
            value={name}
            onSubmit={setName}
            isReadOnly={isReadOnly || !isSelected}
          />
          {isSelected && !isReadOnly
            ? (
              <TabDropdown
                onClickRename={this.handleClickRename}
                onClickDelete={this.handleClickDelete}
                onClickDuplicate={this.handleClickDuplicate}
              />)
            : null}
        </div>
      </li>
    )
  }
}
