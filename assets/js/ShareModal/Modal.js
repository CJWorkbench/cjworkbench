import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../components/Modal'
import PublicPrivate from './PublicPrivate'
import Acl from './Acl'
import Url from './Url'

export default class _Modal extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired, // are we owner? Otherwise, we can't edit the ACL
    url: PropTypes.string.isRequired,
    isPublic: PropTypes.bool.isRequired,
    logShare: PropTypes.func.isRequired, // func('Facebook'|'Twitter'|'URL copied') => undefined
    ownerEmail: PropTypes.string.isRequired,
    acl: PropTypes.arrayOf(PropTypes.shape({
      email: PropTypes.string.isRequired,
      canEdit: PropTypes.bool.isRequired
    }).isRequired), // or null if loading
    setIsPublic: PropTypes.func.isRequired, // func(isPublic) => undefined
    updateAclEntry: PropTypes.func.isRequired, // func(email, canEdit) => undefined
    deleteAclEntry: PropTypes.func.isRequired, // func(email) => undefined
    onClickClose: PropTypes.func.isRequired // func() => undefined
  }

  render () {
    const {
      url, isReadOnly, isPublic, setIsPublic, logShare, ownerEmail, acl,
      updateAclEntry, deleteAclEntry, onClickClose
    } = this.props

    return (
      <Modal className='share-modal' isOpen toggle={onClickClose}>
        <ModalHeader>SHARING SETTINGS</ModalHeader>
        <ModalBody>
          <h6>Share with the world</h6>
          <PublicPrivate
            isReadOnly={isReadOnly}
            isPublic={isPublic}
            setIsPublic={setIsPublic}
          />

          <h6>Collaborators</h6>
          <Acl
            isReadOnly={isReadOnly}
            ownerEmail={ownerEmail}
            acl={acl}
            updateAclEntry={updateAclEntry}
            deleteAclEntry={deleteAclEntry}
          />

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
            >Close
            </button>
          </div>
        </ModalFooter>
      </Modal>
    )
  }
}
