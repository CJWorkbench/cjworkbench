import React from 'react'
import PropTypes from 'prop-types'
import Dropdown from './Dropdown'

export default class UncontrolledDropdown extends React.PureComponent {
  static propTypes = {
    disabled: PropTypes.bool,
    className: PropTypes.string,
    direction: PropTypes.oneOf([ 'up', 'down' ]),
    children: PropTypes.node.isRequired
  }

  state = {
    isOpen: false
  }

  toggleIsOpen = () => {
    this.setState(s => ({ isOpen: !s.isOpen }))
  }

  render () {
    const { isOpen } = this.state

    return (
      // this.props includes .children, 
      <Dropdown isOpen={isOpen} toggle={this.toggleIsOpen} {...this.props} />
    )
  }
}
