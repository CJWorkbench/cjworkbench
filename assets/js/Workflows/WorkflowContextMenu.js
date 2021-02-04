import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'
import { Trans } from '@lingui/macro'
import ShareModal from './ShareModal'

export default function WorkflowContextMenu (props) {
  const {
    workflow,
    onClickDeleteWorkflow,
    onClickDuplicateWorkflow,
    apiForShareModal,
    onWorkflowChanging,
    onWorkflowChanged
  } = props
  const [isShareModalOpen, setShareModalOpen] = React.useState(false)

  const handleClickDelete = React.useCallback(() => {
    onClickDeleteWorkflow(workflow.id)
  }, [workflow, onClickDeleteWorkflow])
  const handleClickDuplicate = React.useCallback(() => {
    onClickDuplicateWorkflow(workflow.id)
  }, [workflow, onClickDuplicateWorkflow])
  const handleClickShare = React.useCallback(() => {
    setShareModalOpen(true)
  }, [setShareModalOpen])
  const handleCloseShareModal = React.useCallback(() => {
    setShareModalOpen(false)
  }, [setShareModalOpen])

  return (
    <>
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-more' />
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem onClick={handleClickShare}>
            <i className='icon-share' />
            <span><Trans id='js.Workflows.WorkflowContextMenu.share'>Share</Trans></span>
          </DropdownItem>
          <DropdownItem onClick={handleClickDuplicate}>
            <i className='icon-duplicate' />
            <span><Trans id='js.Workflows.WorkflowContextMenu.duplicate'>Duplicate</Trans></span>
          </DropdownItem>
          <DropdownItem onClick={handleClickDelete}>
            <i className='icon-bin' />
            <span><Trans id='js.Workflows.WorkflowContextMenu.delete'>Delete</Trans></span>
          </DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
      {isShareModalOpen ? (
        <ShareModal
          workflow={workflow}
          api={apiForShareModal}
          onWorkflowChanging={onWorkflowChanging}
          onWorkflowChanged={onWorkflowChanged}
          onClose={handleCloseShareModal}
        />
      ) : null}
    </>
  )
}
WorkflowContextMenu.propTypes = {
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired
  }).isRequired,
  onClickDeleteWorkflow: PropTypes.func.isRequired, // func(id) => undefined
  onClickDuplicateWorkflow: PropTypes.func.isRequired, // func(id) => undefined
  apiForShareModal: PropTypes.shape({
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, canEdit) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublic: PropTypes.func.isRequired // func(id, isPublic) => Promise[null]
  }).isRequired,
  onWorkflowChanging: PropTypes.func.isRequired, // func(id, {k: v, ...}) => undefined
  onWorkflowChanged: PropTypes.func.isRequired // func(id) => undefined
}
