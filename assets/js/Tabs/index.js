import Tabs from './Tabs'
import { connect } from 'react-redux'
import * as mapDispatchToProps from './actions'

function mapStateToProps (state) {
  const { workflow, tabs } = state
  const pendingTabs = state.pendingTabs ? state.pendingTabs : {}

  return {
    tabs: workflow.tab_slugs.map(slug => tabs[slug] || pendingTabs[slug]),
    selectedTabPosition: workflow.selected_tab_position,
    isReadOnly: workflow.read_only,
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(Tabs)
