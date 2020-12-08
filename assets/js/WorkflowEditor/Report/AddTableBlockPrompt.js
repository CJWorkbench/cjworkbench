import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { Dropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../../components/Dropdown'
import IconTable from '../../../icons/table.svg'

export default function AddTableBlockPrompt ({ tabs, isMenuOpen, onOpenMenu, onCloseMenu, onSubmit }) {
  const handleToggleMenu = isMenuOpen ? onCloseMenu : onOpenMenu
  const handleClick = React.useCallback(ev => {
    onSubmit({ tabSlug: ev.target.getAttribute('data-tab-slug') })
  }, [onSubmit])

  return (
    <Dropdown isOpen={isMenuOpen} toggle={handleToggleMenu}>
      <DropdownToggle
        name='add-table-block'
        title={t({
          id: 'js.WorkflowEditor.Report.AddTableBlockPrompt.hoverText',
          message: 'Add table from tab'
        })}
      >
        <IconTable />
      </DropdownToggle>
      <DropdownMenu>
        {tabs.map(tab => (
          <DropdownItem
            key={tab.slug}
            data-tab-slug={tab.slug}
            onClick={handleClick}
          >
            {tab.name}
          </DropdownItem>
        ))}
      </DropdownMenu>
    </Dropdown>
  )
}
AddTableBlockPrompt.propTypes = {
  tabs: PropTypes.arrayOf(PropTypes.shape({
    slug: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired
  }).isRequired).isRequired,
  isMenuOpen: PropTypes.bool.isRequired,
  onOpenMenu: PropTypes.func.isRequired,
  onCloseMenu: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired // func({ tabSlug }) => undefined
}
