import StepList from './StepList'
import { reorderStep } from './actions'
import { deleteStepAction } from '../../workflow-reducer'
import { connect } from 'react-redux'
import lessonSelector from '../../lessons/lessonSelector'

const mapStateToProps = (state) => {
  const { modules } = state
  const { testHighlight } = lessonSelector(state)
  const tabPosition = state.workflow.selected_tab_position
  const tabSlug = state.workflow.tab_slugs[tabPosition]
  const tab = state.tabs[tabSlug]
  const steps = tab.step_ids.map(id => state.steps[String(id)])
  return {
    workflow: state.workflow,
    selected_step_position: tab.selected_step_position,
    tabSlug,
    steps,
    modules,
    isReadOnly: state.workflow.read_only,
    testLessonHighlightIndex: (index) => testHighlight({ type: 'Module', id_name: null, index: index })
  }
}

const mapDispatchToProps = dispatch => {
  return {
    reorderStep (tabSlug, stepSlug, newIndex) {
      const action = reorderStep(tabSlug, stepSlug, newIndex)
      dispatch(action)
    },

    deleteStep (stepId) {
      const action = deleteStepAction(stepId)
      dispatch(action)
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(StepList)
