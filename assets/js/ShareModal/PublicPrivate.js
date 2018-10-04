import React from 'react'
import PropTypes from 'prop-types'

export default class PublicPrivate extends React.PureComponent {
  static propTypes = {
    isPublic: PropTypes.bool.isRequired,
    onChangeIsPublic: PropTypes.func.isRequired, // func(isPublic) => undefined
  }

  onChangeIsPublic = (ev) => {
    this.props.onChangeIsPublic(ev.target.checked)
  }

  render () {
    const { isPublic, logShare } = this.props
    const className = `public-private ${isPublic ? 'is-public' : 'is-private'}`

    return (
      <div className={className}>
        <label className='checkbox'>
          <input type='checkbox' checked={isPublic} onChange={this.onChangeIsPublic} />
          <span>Allow anybody on the Internet to view and duplicate this Workflow.</span>
        </label>
      </div>
    )
  }
}
