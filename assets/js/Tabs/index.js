import Tabs from './Tabs'
import { connect } from 'react-redux'
import * as mapDispatchToProps from './actions'

function mapStateToProps (state) {
  const { workflow, tabs } = state

  return {
    tabs: workflow.tab_ids.map(id => tabs[String(id)]),
    selectedTabPosition: workflow.selected_tab_position,
    nPendingCreates: tabs.nPendingCreates || 0,
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(Tabs)
