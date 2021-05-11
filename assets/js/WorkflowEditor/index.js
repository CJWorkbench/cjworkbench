import { connect } from 'react-redux'
import WorkflowEditor from './WorkflowEditor'
import { selectReportPaneAction } from './actions'
import selectOptimisticState from '../selectors/selectOptimisticState'

function mapStateToProps (state) {
  const { selectedPane } = selectOptimisticState(state)
  return { selectedPane }
}

const mapDispatchToProps = {
  selectReportPane: selectReportPaneAction
}

export default connect(mapStateToProps, mapDispatchToProps)(WorkflowEditor)
