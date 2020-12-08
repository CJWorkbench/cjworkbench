import React from 'react'
import PropTypes from 'prop-types'
import * as propTypes from './propTypes'
import Tabs from './Tabs'
import { t, Trans } from '@lingui/macro'
import IconReport from '../../icons/report.svg'

export default function PaneSelect ({ selectedPane, selectReportPane }) {
  return (
    <nav className={`pane-select selected-${selectedPane.pane}`}>
      <Tabs />
      <div className='report'>
        <button
          type='button'
          title={t({
            id: 'js.WorkflowEditor.PaneSelect.nav.reportPlaceholder',
            message: 'Report'
          })}
          onClick={selectReportPane}
          disabled={selectedPane.pane === 'report'}
        >
          <IconReport />
          <Trans id='js.WorkflowEditor.PaneSelect.nav.report' comment='This is a link to a report'>Report</Trans>
        </button>
      </div>
    </nav>
  )
}
PaneSelect.propTypes = {
  selectedPane: propTypes.selectedPane.isRequired,
  selectReportPane: PropTypes.func.isRequired // func() => undefined
}
