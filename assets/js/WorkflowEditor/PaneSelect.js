import PropTypes from 'prop-types'
import * as propTypes from './propTypes'
import Tabs from './Tabs'
import { Trans } from '@lingui/macro'
import IconReport from '../../icons/report.svg'
import IconDataset from '../../icons/dataset.svg'

export default function PaneSelect (props) {
  const { selectedPane, selectDatasetPublisherPane, selectReportEditorPane } = props

  return (
    <nav className={`pane-select selected-${selectedPane.pane}`}>
      <Tabs />
      <div className='report'>
        <button
          type='button'
          onClick={selectReportEditorPane}
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
        <button
          type='button'
          onClick={selectDatasetPublisherPane}
          disabled={selectedPane.pane === 'dataset'}
        >
          <IconDataset />
          <Trans
            id='js.WorkflowEditor.PaneSelect.nav.dataset'
            comment='Link to the dataset publisher'
          >
            Dataset Publisher
          </Trans>
        </button>
      </div>
    </nav>
  )
}
PaneSelect.propTypes = {
  selectedPane: propTypes.selectedPane.isRequired,
  selectDatasetPublisherPane: PropTypes.func.isRequired, // func() => undefined
  selectReportEditorPane: PropTypes.func.isRequired // func() => undefined
}
