import React from 'react'
import PropTypes from 'prop-types'
import { ModalContext } from './Modal'

export default class ModalHeader extends React.PureComponent {
  static propTyes = {
    children: PropTypes.node.isRequired
  }

  static contextType = ModalContext

  render () {
    const { children } = this.props
    const { toggle } = this.context

    return (
      <div className='modal-header'>
        <h5 className='modal-title'>{children}</h5>
        <button type='button' className='close' aria-label='Close' onClick={toggle}>
          <span aria-hidden='true'>×</span>
        </button>
      </div>
    )
  }
}
