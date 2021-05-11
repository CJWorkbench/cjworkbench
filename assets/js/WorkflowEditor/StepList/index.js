import StepList from './StepList'
import { reorderStep } from './actions'
import { deleteStepAction } from '../../workflow-reducer'
import { connect } from 'react-redux'
import selectIsReadOnly from '../../selectors/selectIsReadOnly'
import selectOptimisticState from '../../selectors/selectOptimisticState'
import lessonSelector from '../../lessons/lessonSelector'

function mapStateToProps (state) {
  const { modules, selectedPane, steps, tabs } = selectOptimisticState(state)
  const { testHighlight } = lessonSelector(state)
  const tabSlug = selectedPane.tabSlug
  const tab = tabs[tabSlug]
  const tabSteps = tab.step_ids.map(id => steps[String(id)])
  return {
    workflow: state.workflow,
    selected_step_position: tab.selected_step_position,
    tabSlug,
    steps: tabSteps,
    modules,
    isReadOnly: selectIsReadOnly(state),
    testLessonHighlightIndex: index =>
      testHighlight({ type: 'Module', id_name: null, index: index })
  }
}

function mapDispatchToProps (dispatch) {
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

export default connect(mapStateToProps, mapDispatchToProps)(StepList)
