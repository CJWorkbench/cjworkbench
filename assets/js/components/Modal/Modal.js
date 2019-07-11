import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'

export const ModalContext = React.createContext()
ModalContext.Provider.propTypes = {
  value: PropTypes.shape({
    toggle: PropTypes.func.isRequired // func() => undefined; should close the modal
  }).isRequired
}

export const FocusableElementsSelector = [
  'a[href]',
  'area[href]',
  'input:enabled:not([type=hidden])',
  'select:enabled',
  'textarea:enabled',
  'button:enabled',
  'object',
  'embed',
  '[tabindex]:not([tabindex="-1"])',
  'audio[controls]',
  'video[controls]',
  '[contenteditable]:not([contenteditable="false"])'
].join(',')

class OpenModal extends React.PureComponent {
  static propTypes = {
    children: PropTypes.node.isRequired,
    toggle: PropTypes.func.isRequired, // func() => undefined; should close the modal
    className: PropTypes.string, // will be added to 'modal'
    size: PropTypes.oneOf([ 'lg', 'sm' ]) // if set, .modal-dialog becomes .modal-dialog.modal-lg
  }

  modalRef = React.createRef()

  /**
   * Focus the "next" (by=1) or "previous" (by=-1) focusable HTML element.
   *
   * Implements the algorithm described at:
   * https://developers.google.com/web/fundamentals/accessibility/focus/using-tabindex
   */
  moveFocusBy = (by) => {
    if (!this.modalRef.current) return

    const oldActiveElement = document.activeElement

    // els should never be zero-length: the "close" button is tab-indexable
    const els = [ ...this.modalRef.current.querySelectorAll(FocusableElementsSelector) ]
    const index = els.indexOf(oldActiveElement) // may be -1

    let nextIndex = index
    do {
      nextIndex += by
      if (nextIndex < 0) nextIndex = els.length - 1
      if (nextIndex >= els.length) nextIndex = 0
      els[nextIndex].focus()
      // el.focus() isn't guaranteed to _work_. For instance, we can't focus
      // elements with display:none in Chrome 72 on Linux. Loop until we
      // succeed in focusing an element.
    } while (document.activeElement === oldActiveElement)
  }

  componentDidMount () {
    document.body.classList.add('modal-open')
    this.previouslyFocusedElement = document.activeElement
    this.moveFocusBy(1)
  }

  componentWillUnmount () {
    document.body.classList.remove('modal-open')
    if (this.previouslyFocusedElement) this.previouslyFocusedElement.focus()
  }

  onMouseDown = (ev) => {
    if (ev.target === this.modalRef.current) {
      this.props.toggle(ev)
    }
  }

  /**
   * Keyboard handler:
   *
   * * "Escape" -> close dialog
   * * "Tab" / "Shift-Tab" -> select next/previous element
   */
  onKeyDown = (ev) => {
    switch (ev.key) {
      case 'Tab':
        ev.preventDefault()
        ev.stopPropagation()
        this.moveFocusBy(ev.shiftKey ? -1 : 1)
        return

      case 'Escape':
        ev.preventDefault()
        ev.stopPropagation()
        this.props.toggle(ev)
    }
  }

  render () {
    const { children, toggle, className, size } = this.props
    const modalContext = { toggle }

    const classNames = [ 'modal' ]
    if (className) classNames.push(className)

    const dialogClassNames = [ 'modal-dialog' ]
    if (size) dialogClassNames.push(`modal-${size}`)

    return ReactDOM.createPortal((
      <ModalContext.Provider value={modalContext}>
        <div className='modal-backdrop' />
        <div
          className={classNames.join(' ')}
          ref={this.modalRef}
          onMouseDown={this.onMouseDown}
          onKeyDown={this.onKeyDown}
          tabIndex='-1'
          role='dialog'
        >
          <div className={dialogClassNames.join(' ')} role='document'>
            <div className='modal-content' children={children} />
          </div>
        </div>
      </ModalContext.Provider>
    ), document.body)
  }
}

/**
 * Modal dialog.
 *
 * Design decisions:
 * * There's no fade-in/fade-out animation.
 * * If the modal is closed, it's not rendered at all.
 * * We use a Portal, always.
 *
 * https://getbootstrap.com/docs/4.0/components/modal/
 */
export default class Modal extends React.PureComponent {
  static propTypes = {
    children: PropTypes.node.isRequired,
    toggle: PropTypes.func.isRequired, // func() => undefined; should close the modal
    className: PropTypes.string, // will be added to 'modal'
    isOpen: PropTypes.bool.isRequired, // if false, render null
    size: PropTypes.oneOf([ 'lg', 'sm' ]) // if set, .modal-dialog becomes .modal-dialog.modal-lg
  }

  render () {
    const { isOpen, ...rest } = this.props
    if (!isOpen) return null

    return <OpenModal {...rest} />
  }
}
