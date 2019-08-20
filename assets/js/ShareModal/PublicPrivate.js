import React from 'react'
import PropTypes from 'prop-types'

const Description = ({ isPublic }) => {
  const message = isPublic
    ? 'Anyone on the Internet may view and duplicate this Workflow.'
    : 'Only collaborators can view this Workflow.'

  return (
    <p>{message}</p>
  )
}

const DescriptionWithToggle = ({ isPublic, onChange }) => (
  <label className='checkbox'>
    <input type='checkbox' checked={isPublic} onChange={onChange} />
    <span>Anyone can view and duplicate this workflow, and see your email.</span>
  </label>
)

export default class PublicPrivate extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired, // are we owner? Otherwise, we can't edit the ACL
    isPublic: PropTypes.bool.isRequired,
    setIsPublic: PropTypes.func.isRequired // func(isPublic) => undefined
  }

  handleChangeIsPublic = (ev) => {
    const { isReadOnly, setIsPublic } = this.props
    if (isReadOnly) return // should be redundant
    setIsPublic(ev.target.checked)
  }

  render () {
    const { isReadOnly, isPublic } = this.props
    const className = `public-private ${isPublic ? 'is-public' : 'is-private'} ${isReadOnly ? 'read-only' : 'read-write'}`

    return (
      <div className={className}>
        {isReadOnly ? (
          <Description isPublic={isPublic} />
        ) : (
          <DescriptionWithToggle isPublic={isPublic} onChange={this.handleChangeIsPublic} />
        )}
      </div>
    )
  }
}
