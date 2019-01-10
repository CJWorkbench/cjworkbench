import React from 'react'
import PropTypes from 'prop-types'

export default class UndoRedoButtons extends React.PureComponent {
  static propTypes = {
    undo: PropTypes.func.isRequired, // func() => undefined
    redo: PropTypes.func.isRequired // func() => undefined
  }

  onDocumentKeyDown = (ev) => {
    const { undo, redo } = this.props

    // Ignore keypresses when they're users inputting into things.
    //
    // Custom components that want to eat keydowns should
    // .stopPropagation() or .preventDefault() to have this method ignore them.
    switch (ev.target.tagName) {
      case 'INPUT':
      case 'TEXTAREA':
      case 'SELECT':
      case 'OPTION':
        return
    }

    // Check whether a React component is trying to tell us to ignore this
    // event.
    if (ev.defaultPrevented) return

    if (ev.metaKey || ev.ctrlKey) {  // Meta on OS X, Ctrl on Windows
      switch (ev.key) {
        case 'z':
          if (ev.shiftKey) {
            // Mac OS standard for "redo" is Meta+Shift+z
            return redo()
          } else {
            return undo()
          }
        case 'y':
          // Windows/Linux standard for "redo" is Meta+y
          return redo()
      }
    }
  }

  componentDidMount () {
    document.addEventListener('keydown', this.onDocumentKeyDown)
  }

  componentWillUnmount () {
    document.removeEventListener('keydown', this.onDocumentKeyDown)
  }

  render () {
    const { undo, redo } = this.props

    return (
      <div className='group--undo-redo'>
        <button name='undo' title='Undo' onClick={undo}><i className='icon-undo' /></button>
        <button name='redo' title='Redo' onClick={redo}><i className='icon-redo' /></button>
      </div>
    )
  }
}
