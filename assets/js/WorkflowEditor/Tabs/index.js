import Tabs from './Tabs'
import { connect } from 'react-redux'
import * as mapDispatchToProps from './actions'
import selectIsReadOnly from '../../selectors/selectIsReadOnly'
import selectOptimisticState from '../../selectors/selectOptimisticState'

function mapStateToProps (state) {
  const { selectedPane, workflow, tabs } = selectOptimisticState(state)

  return {
    tabs: workflow.tab_slugs.map(slug => tabs[slug]),
    selectedPane,
    isReadOnly: selectIsReadOnly(state)
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(Tabs)
