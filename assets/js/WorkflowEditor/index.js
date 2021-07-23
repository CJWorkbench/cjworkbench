import { connect } from 'react-redux'
import { selectDatasetPublisherPaneAction, selectReportPaneAction } from './actions'
import WorkflowEditor from './WorkflowEditor'

const mapStateToProps = ({ selectedPane }) => {
  return { selectedPane }
}

const mapDispatchToProps = {
  selectDatasetPublisherPane: selectDatasetPublisherPaneAction,
  selectReportEditorPane: selectReportPaneAction
}

export default connect(mapStateToProps, mapDispatchToProps)(WorkflowEditor)
