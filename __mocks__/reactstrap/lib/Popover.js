import React from 'react'

export default class Popover extends React.PureComponent {
  render () {
    const { innerClassName, isOpen } = this.props
    if (!isOpen) return null

    const props = { ...this.props }
    delete props.isOpen
    delete props.innerClassName
    delete props.toggle
    delete props.target
    delete props.boundariesElement

    props.className = innerClassName || null

    return (
      <div className='mock-reactstrap-Popover'>
        <div {...props}/>
      </div>
    )
  }
}
