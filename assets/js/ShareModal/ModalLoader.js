import React from 'react'
import PropTypes from 'prop-types'
import Modal from './Modal'

/**
 * Wraps a Modal with HTTP requests to maintain the collaborator list.
 */
export default class ModalLoader extends React.PureComponent {
  static propTypes = {
    api: PropTypes.object.isRequired,
    isReadOnly: PropTypes.bool.isRequired, // are we owner? Otherwise, we can't edit the ACL
    workflowId: PropTypes.number.isRequired,
    url: PropTypes.string.isRequired,
    isPublic: PropTypes.bool.isRequired,
    ownerEmail: PropTypes.string.isRequired,
    onChangeIsPublic: PropTypes.func.isRequired, // func(isPublic) => undefined
    logShare: PropTypes.func.isRequired, // func('Facebook'|'Twitter'|'URL copied') => undefined
    onClickClose: PropTypes.func.isRequired // func() => undefined
  }

  state = {
    acl: null // null when loading
  }

  componentDidMount () {
    const { workflowId } = this.props
    this.props.api.getAcl(workflowId)
      .then(acl => {
        if (this.unmounted) return
        this.setState({ acl })
      })
  }

  componentWillUnmount () {
    this.unmounted = true
  }

  updateAclEntry = (email, canEdit) => {
    const { isReadOnly, ownerEmail, workflowId } = this.props
    if (isReadOnly) return // should be redundant
    if (email === ownerEmail) return

    this.props.api.updateAclEntry(workflowId, email, canEdit)

    this.setState(state => {
      const acl = state.acl.slice() // shallow copy

      let index = acl.findIndex(entry => entry.email === email)
      if (index === -1) index = acl.length

      // overwrite or append the specified ACL entry
      acl[index] = { email, canEdit }

      acl.sort((a, b) => a.email.localeCompare(b.email))

      return { acl }
    })
  }

  deleteAclEntry = (email) => {
    const { isReadOnly, ownerEmail, workflowId } = this.props
    if (isReadOnly) return // should be redundant
    if (email === ownerEmail) return

    this.props.api.deleteAclEntry(workflowId, email)

    this.setState(state => {
      return { acl: state.acl.filter(entry => entry.email !== email) }
    })
  }

  render () {
    const { url, isPublic, isReadOnly, onChangeIsPublic, ownerEmail, logShare, onClickClose } = this.props
    const { acl } = this.state

    return (
      <Modal
        url={url}
        isReadOnly={isReadOnly}
        isPublic={isPublic}
        ownerEmail={ownerEmail}
        onChangeIsPublic={onChangeIsPublic}
        logShare={logShare}
        acl={acl}
        onChangeAclEntry={this.updateAclEntry}
        onCreateAclEntry={this.updateAclEntry}
        onClickDeleteAclEntry={this.deleteAclEntry}
        onClickClose={onClickClose}
      />
    )
  }
}
