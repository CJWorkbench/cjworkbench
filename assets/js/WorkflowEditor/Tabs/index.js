import Tabs from './Tabs'
import { connect } from 'react-redux'
import * as mapDispatchToProps from './actions'
import selectIsReadOnly from '../../selectors/selectIsReadOnly'

function getTab (slug, tabs, pendingTabs) {
  if (slug in tabs) {
    return tabs[slug]
  } else {
    return {
      // Defaults (defensive programming)
      slug: '',
      name: '',
      // UI-specific properties (not in store)
      isPending: true,
      // Actual tab data
      ...(pendingTabs[slug] || {})
    }
  }
}

function mapStateToProps (state) {
  const { selectedPane, workflow, tabs } = state
  const pendingTabs = state.pendingTabs ? state.pendingTabs : {}

  return {
    tabs: workflow.tab_slugs.map(slug => getTab(slug, tabs, pendingTabs)),
    selectedPane,
    isReadOnly: selectIsReadOnly(state)
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(Tabs)
