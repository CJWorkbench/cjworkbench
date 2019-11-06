// Drop-down menu at upper right of each module in a workflow
import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../../components/Dropdown'
import ExportModal from '../../ExportModal'
import { Trans } from '@lingui/macro'

const WfModuleContextMenu = React.memo(function WfModuleContextMenu ({ removeModule, id }) {
  const [isExportModalOpen, setExportModalOpen] = React.useState(false)
  const handleClickOpenExportModal = React.useCallback(() => setExportModalOpen(true))
  const handleCloseExportModal = React.useCallback(() => setExportModalOpen(false))
  const handleClickDelete = React.useCallback(() => removeModule(id))

  return (
    <UncontrolledDropdown>
      <DropdownToggle title='more' className='context-button'>
        <i className='icon-more' />
      </DropdownToggle>
      <DropdownMenu>
        <DropdownItem onClick={handleClickOpenExportModal} className='test-export-button' icon='icon-download'><Trans id='js.WorkflowEditor.wfmodule.wfModuleContextMenu.exportData'>Export data</Trans></DropdownItem>
        <DropdownItem onClick={handleClickDelete} className='test-delete-button' icon='icon-bin'><Trans id='js.WorkflowEditor.wfmodule.wfModuleContextMenu.delete'>Delete</Trans></DropdownItem>
      </DropdownMenu>
      <ExportModal open={isExportModalOpen} wfModuleId={id} toggle={handleCloseExportModal} />
    </UncontrolledDropdown>
  )
})
WfModuleContextMenu.propTypes = {
  removeModule: PropTypes.func,
  id: PropTypes.number
}
export default WfModuleContextMenu
