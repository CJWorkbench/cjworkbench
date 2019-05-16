import { connect } from 'react-redux'
import { selectReportPaneAction } from './actions'
import WorkflowEditor from './WorkflowEditor'

const mapStateToProps = ({ selectedPane }) => {
  return { selectedPane }
}

const mapDispatchToProps = {
  selectReportPane: selectReportPaneAction
}

export default connect(mapStateToProps, mapDispatchToProps)(WorkflowEditor)
