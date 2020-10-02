import Dashboard from './Dashboard'
import { connect } from 'react-redux'

function mapStateToProps (state) {
  const { workflow, tabs, steps, modules } = state
  const allTabs = workflow.tab_slugs.map(s => tabs[s]).filter(t => !!t)
  const tabsWithStepsWithIframe = allTabs
    .map(tab => {
      const stepsWithIframe = tab.step_ids
        .map(id => steps[String(id)])
        .filter(s => !!s && modules[s.module] && modules[s.module].has_html_output)
        .map(step => ({
          id: step.id,
          deltaId: step.last_relevant_delta_id
        }))
      return {
        slug: tab.slug,
        name: tab.name,
        steps: stepsWithIframe
      }
    })
    .filter(tab => tab.steps.length)

  return {
    workflowId: workflow.id,
    isPublic: workflow.public,
    tabs: tabsWithStepsWithIframe
  }
}

export default connect(mapStateToProps)(Dashboard)
