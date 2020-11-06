import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../../components/Dropdown'

function AddChartBlockPrompt ({ onSubmit, tabs, i18n }) {
  const handleClick = React.useCallback(ev => {
    onSubmit({ stepSlug: ev.target.getAttribute('data-step-slug') })
  }, [onSubmit])
  const hasSteps = tabs.some(tab => tab.chartSteps.length > 0)

  return (
    <UncontrolledDropdown disabled={!hasSteps}>
      <DropdownToggle
        className='button-gray'
        title={i18n._(t('js.WorkflowEditor.Report.AddChartBlockPrompt.hoverText')`Add chart`)}
      >
        <i className='icon icon-chart' />
      </DropdownToggle>
      <DropdownMenu>
        {tabs.map(({ slug: tabSlug, name: tabName, chartSteps }) => (
          <React.Fragment key={tabSlug}>
            {chartSteps.map(({ slug: stepSlug, moduleName }) => (
              <DropdownItem
                key={stepSlug}
                data-step-slug={stepSlug}
                onClick={handleClick}
              >
                <Trans id='js.WorkflowEditor.Report.AddChartBlockPrompt.tabAndChartName'>{tabName} – {moduleName}</Trans>
              </DropdownItem>
            ))}
          </React.Fragment>
        ))}
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}
AddChartBlockPrompt.propTypes = {
  tabs: PropTypes.arrayOf(PropTypes.shape({
    slug: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    chartSteps: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      moduleName: PropTypes.string.isRequired
    }).isRequired).isRequired
  }).isRequired).isRequired,
  onSubmit: PropTypes.func.isRequired // func({ tabSlug }) => undefined
}
export default withI18n()(AddChartBlockPrompt)
