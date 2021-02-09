/* globals confirm */
import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'
import { Trans, t } from '@lingui/macro'
import ShareModal from './ShareModal'
import ContextMenuIcon from '../../icons/context-menu.svg'

export default function WorkflowContextMenu (props) {
  const {
    workflow,
    api,
    onWorkflowChanging,
    onWorkflowChanged,
    onWorkflowDuplicating,
    onWorkflowDuplicated
  } = props
  const [isShareModalOpen, setShareModalOpen] = React.useState(false)

  const handleClickDelete = React.useCallback(() => {
    if (!confirm(
      t({ id: 'js.Workflows.delete.permanentyDeleteWarning', message: 'Permanently delete this workflow?' })
    )) {
      return
    }

    onWorkflowChanging(workflow.id, { isDeleted: true })
    api.deleteWorkflow(workflow.id).then(() => onWorkflowChanged(workflow.id))
  }, [api, workflow, onWorkflowChanging, onWorkflowChanged])
  const handleClickDuplicate = React.useCallback(() => {
    onWorkflowDuplicating(workflow.id, {})
    api.duplicateWorkflow(workflow.id).then(json => {
      onWorkflowDuplicated(workflow.id, json)
    })
  }, [api, workflow, onWorkflowDuplicating, onWorkflowDuplicated])
  const handleClickShare = React.useCallback(() => {
    setShareModalOpen(true)
  }, [setShareModalOpen])
  const handleCloseShareModal = React.useCallback(() => {
    setShareModalOpen(false)
  }, [setShareModalOpen])

  return (
    <>
      <UncontrolledDropdown>
        <DropdownToggle
          className='icon-button'
          title={t({ id: 'js.Workflows.WorkflowContextMenu.hoverText', message: 'menu' })}
        >
          <ContextMenuIcon />
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
          api={api}
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
  api: PropTypes.shape({
    deleteWorkflow: PropTypes.func.isRequired, // func(id) => Promise[null]
    duplicateWorkflow: PropTypes.func.isRequired, // func(id) => Promise[{ id, name }]
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, canEdit) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublic: PropTypes.func.isRequired // func(id, isPublic) => Promise[null]
  }).isRequired,
  onWorkflowChanging: PropTypes.func.isRequired, // func(id, {k: v, ...}) => undefined
  onWorkflowChanged: PropTypes.func.isRequired, // func(id) => undefined
  onWorkflowDuplicating: PropTypes.func.isRequired, // func(id, {k: v, ...}) => undefined
  onWorkflowDuplicated: PropTypes.func.isRequired // func(id) => undefined
}
