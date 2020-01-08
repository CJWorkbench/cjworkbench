import Dashboard from './Dashboard'
import { connect } from 'react-redux'

function mapStateToProps (state) {
  const { workflow, tabs, wfModules, modules } = state
  const allTabs = workflow.tab_slugs.map(s => tabs[s]).filter(t => !!t)
  const tabsWithWfModulesWithIframe = allTabs
    .map(tab => {
      const wfModulesWithIframe = tab.wf_module_ids
        .map(id => wfModules[String(id)])
        .filter(s => !!s && modules[s.module] && modules[s.module].has_html_output)
        .map(wfm => ({
          id: wfm.id,
          deltaId: wfm.last_relevant_delta_id
        }))
      return {
        slug: tab.slug,
        name: tab.name,
        wfModules: wfModulesWithIframe
      }
    })
    .filter(tab => tab.wfModules.length)

  return {
    workflowId: workflow.id,
    isPublic: workflow.public,
    tabs: tabsWithWfModulesWithIframe
  }
}

export default connect(mapStateToProps)(Dashboard)
