import PropTypes from 'prop-types'
import * as propTypes from './propTypes'
import Tabs from './Tabs'
import { Trans } from '@lingui/macro'
import IconReport from '../../icons/report.svg'

export default function PaneSelect ({ selectedPane, selectReportPane }) {
  return (
    <nav className={`pane-select selected-${selectedPane.pane}`}>
      <Tabs />
      <div className='report'>
        <button
          type='button'
          onClick={selectReportPane}
          disabled={selectedPane.pane === 'report'}
        >
          <IconReport />
          <Trans
            id='js.WorkflowEditor.PaneSelect.nav.report'
            comment='Link to the report editor'
          >
            Report Editor
          </Trans>
        </button>
      </div>
    </nav>
  )
}
PaneSelect.propTypes = {
  selectedPane: propTypes.selectedPane.isRequired,
  selectReportPane: PropTypes.func.isRequired // func() => undefined
}
