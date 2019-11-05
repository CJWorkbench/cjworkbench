import React from 'react'
import PropTypes from 'prop-types'
import * as propTypes from './propTypes'
import Tabs from './Tabs'
import { Trans } from '@lingui/macro'

const PaneSelect = React.memo(function PaneSelect ({ selectedPane, selectReportPane }) {
  return (
    <nav className={`pane-select selected-${selectedPane.pane}`}>
      <Tabs />
      <div className='report'>
        <button
          type='button'
          title='Report'
          onClick={selectReportPane}
          disabled={selectedPane.pane === 'report'}
        >
          <i className='icon icon-chart' />
          <Trans id='js.WorkflowEditor.PaneSelect.nav.report' description='This is a link to a report'>Report</Trans>
        </button>
      </div>
    </nav>
  )
})
PaneSelect.propTypes = {
  selectedPane: propTypes.selectedPane.isRequired,
  selectReportPane: PropTypes.func.isRequired // func() => undefined
}
export default PaneSelect
