import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../../components/Dropdown'

function AddTableBlockPrompt ({ onSubmit, tabs, i18n }) {
  const handleClick = React.useCallback(ev => {
    onSubmit({ tabSlug: ev.target.getAttribute('data-tab-slug') })
  }, [onSubmit])

  return (
    <UncontrolledDropdown>
      <DropdownToggle
        className='button-gray'
        title={i18n._(t('js.WorkflowEditor.Report.AddTableBlockPrompt.hoverText')`Add table from tab`)}
      >
        <i className='icon icon-columns' />
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
    </UncontrolledDropdown>
  )
}
AddTableBlockPrompt.propTypes = {
  tabs: PropTypes.arrayOf(PropTypes.shape({
    slug: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired
  }).isRequired).isRequired,
  onSubmit: PropTypes.func.isRequired // func({ tabSlug }) => undefined
}
export default withI18n()(AddTableBlockPrompt)
