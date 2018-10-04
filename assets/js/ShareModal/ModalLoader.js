import React from 'react'
import PropTypes from 'prop-types'
import Modal from './Modal'
import WorkbenchAPI from '../WorkbenchAPI'

/**
 * Wraps a Modal with HTTP requests to maintain the collaborator list.
 */
export default class LoadingModal extends React.PureComponent {
  static propTypes = {
    workflowId: PropTypes.number.isRequired,
    url: PropTypes.string.isRequired,
    isPublic: PropTypes.bool.isRequired,
    onChangeIsPublic: PropTypes.func.isRequired, // func(isPublic) => undefined
    logShare: PropTypes.func.isRequired, // func('Facebook'|'Twitter'|'URL copied') => undefined
    acl: PropTypes.arrayOf(PropTypes.shape({
      email: PropTypes.string.isRequired,
      canEdit: PropTypes.bool.isRequired
    }).isRequired), // or null if loading
    onClickClose: PropTypes.func.isRequired // func() => undefined
  }

  state = {
    acl: null
  }

  componentDidMount () {
    const { workflowId } = this.props
    WorkbenchAPI.getAcl(workflowId)
      .then(acl => {
        if (this.unmounted) return
        this.setState({ acl })
      })
  }

  componentWillUnmount () {
    this.unmounted = true
  }

  updateAclEntry = (email, canEdit) => {
    const { workflowId } = this.props
    WorkbenchAPI.updateAclEntry(workflowId, email, canEdit)

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
    const { workflowId } = this.props
    WorkbenchAPI.deleteAclEntry(workflowId, email)

    this.setState(state => {
      return { acl: state.acl.filter(entry => entry.email !== email) }
    })
  }

  render () {
    const { url, isPublic, onChangeIsPublic, logShare, onClickClose } = this.props
    const { acl } = this.state

    return (
      <Modal
        url={url}
        isPublic={isPublic}
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
