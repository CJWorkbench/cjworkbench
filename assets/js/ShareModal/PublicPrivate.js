import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

const Description = ({ isPublic }) => {
  const message = isPublic
    ? <Trans id='js.ShareModal.PublicPrivate.description.public'>Anyone on the Internet may view and duplicate this Workflow.</Trans>
    : <Trans id='js.ShareModal.PublicPrivate.description.private'>Only collaborators can view this Workflow.</Trans>
  return (
    <p>{message}</p>
  )
}

const DescriptionWithToggle = ({ isPublic, onChange }) => (
  <label className='checkbox'>
    <input type='checkbox' checked={isPublic} onChange={onChange} />
    <span>
      <Trans id='js.ShareModal.PublicPrivate.descriptionWithToggle'>
            Anyone can view and duplicate this workflow, and see your email.
      </Trans>
    </span>
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
