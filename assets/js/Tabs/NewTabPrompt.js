import React from 'react'
import PropTypes from 'prop-types'

export default class NewTabPrompt extends React.PureComponent {
  static propTypes = {
    create: PropTypes.func.isRequired, // func() => undefined
  }

  render () {
    const { create } = this.props
    return <button className='new-tab' onClick={create}>+</button>
  }
}
