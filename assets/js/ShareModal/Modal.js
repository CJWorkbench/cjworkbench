import React from 'react'
import PropTypes from 'prop-types'
import ReactstrapModal from 'reactstrap/lib/Modal'
import ModalHeader from 'reactstrap/lib/ModalHeader'
import ModalBody from 'reactstrap/lib/ModalBody'
import ModalFooter from 'reactstrap/lib/ModalFooter'
import PublicPrivate from './PublicPrivate'
import Acl from './Acl'
import Url from './Url'

export default class Modal extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired, // are we owner? Otherwise, we can't edit the ACL
    url: PropTypes.string.isRequired,
    isPublic: PropTypes.bool.isRequired,
    onChangeIsPublic: PropTypes.func.isRequired, // func(isPublic) => undefined
    logShare: PropTypes.func.isRequired, // func('Facebook'|'Twitter'|'URL copied') => undefined
    ownerEmail: PropTypes.string.isRequired,
    acl: PropTypes.arrayOf(PropTypes.shape({
      email: PropTypes.string.isRequired,
      canEdit: PropTypes.bool.isRequired
    }).isRequired), // or null if loading
    onChangeAclEntry: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    onCreateAclEntry: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    onClickDeleteAclEntry: PropTypes.func.isRequired, // func(email) => undefined
    onClickClose: PropTypes.func.isRequired // func() => undefined
  }

  render () {
    const { url, isReadOnly, isPublic, onChangeIsPublic, logShare, ownerEmail, acl,
      onChangeAclEntry, onCreateAclEntry, onClickDeleteAclEntry, onClickClose } = this.props

    return (
      <ReactstrapModal className='share-modal' isOpen={true} toggle={onClickClose}>
        <ModalHeader toggle={onClickClose}>SHARING SETTINGS</ModalHeader>
        <ModalBody>
          <h6>Share with the world</h6>
          <PublicPrivate
            isReadOnly={isReadOnly}
            isPublic={isPublic}
            onChangeIsPublic={onChangeIsPublic}
          />

          <h6>Share with collaborators</h6>
          {acl ? (
            <Acl
              isReadOnly={isReadOnly}
              ownerEmail={ownerEmail}
              acl={acl}
              onChange={onChangeAclEntry}
              onCreate={onCreateAclEntry}
              onClickDelete={onClickDeleteAclEntry}
            />
          ) : (
            <div className='loading'>Loading collaborators…</div>
          )}

          <Url
            url={url}
            isPublic={isPublic}
            logShare={logShare}
          />
        </ModalBody>
        <ModalFooter>
          <div className='actions'>
            <button
              name='close'
              className='action-button button-gray'
              onClick={onClickClose}
              >Close</button>
          </div>
        </ModalFooter>
      </ReactstrapModal>
    )
  }
}
