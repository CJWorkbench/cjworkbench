import { createSelector } from 'reselect'
import { StateWithHelpers } from '../lessons/DoneHelpers'
import { matchLessonHighlight } from '../util/LessonHighlight'

function isStepDone(sectionTitle, stepIndex, stateWithHelpers, step) {
  // Canonical example testJs:
  // `return workflow.selectedWfModule.moduleName === 'Add from URL'`
  const fn = new Function('state', 'workflow', '"use strict"; ' + step.testJs)
  // Give our function a name: makes it easy to debug crashes
  Object.defineProperty(fn, 'name', {
    value: `LessonSection "${sectionTitle}" Step ${stepIndex + 1}`,
    writable: false,
  })

  try {
    return fn(stateWithHelpers, stateWithHelpers.workflow)
  } catch (e) {
    console.error(e)
    console.error('The previous error is a bug in this function, called with these arguments:', fn, stateWithHelpers, stateWithHelpers.workflow)
    return false
  }
}

function calculateActiveStep(stateWithHelpers, sections) {
  // Run each testJs function until one returns false
  for (let sectionIndex = 0; sectionIndex < sections.length; sectionIndex++) {
    const section = sections[sectionIndex]
    const steps = section.steps || []
    for (let stepIndex = 0; stepIndex < steps.length; stepIndex++) {
      const step = steps[stepIndex]
      if (!isStepDone(section.title, stepIndex, stateWithHelpers, step)) {
        return {
          activeSectionIndex: sectionIndex,
          activeStepIndex: stepIndex,
          activeStep: step,
        }
      }
    }
  }

  // all steps complete
  return {
    activeSectionIndex: null,
    activeStepIndex: null,
    activeStep: null,
  }
}

/**
 * Return `false` always, so no component gets lesson-highlighted when there
 * is no lesson.
 */
function testLessonHighlightButThereIsNoLesson(test) { return false }

const getWorkflow = ({ workflow }) => workflow
const getTabs = ({ tabs }) => tabs
const getWfModules = ({ wfModules }) => wfModules
const getModules = ({ modules }) => modules
const getSelectedWfModule = ({ selected_wf_module }) => selected_wf_module
const getLessonData = ({ lessonData }) => lessonData || null

/**
 * Returns the Lesson for the given state.
 *
 * Example:
 *
 * ```
 * import lessonSelector from '../lessons/lessonSelector'
 * function mapStateToProps(state, ownProps) {
 *   const { testHighlight } = lessonSelector(state)
 *   return {
 *     isLessonHighlight: testHighlight({ type: 'WfModule', moduleName: ownProps.moduleName })
 *   }
 * }
 * ```
 *
 * The returned object has the following properties:
 *
 * * `activeSectionIndex`: section containing the step we have arrived at
 * * `activeStepIndex`: step within the section that the user needs to complete
 * * `testHighlight`: function that accepts a `LessonHighlightType` and
 *                          returns `true` iff the active step specifies we
 *                          should highlight it.
 *
 * This function never throws. Lessons may have invalid `testJs` values,
 * especially if they index into arrays and the user does something we don't
 * expect. Those errors will be caught and logged with console.error(). An
 * erroring step counts as unfinished: usually, errors mean we haven't imagined
 * a user doing something -- which probably means the user _didn't_ do what we
 * suggested.
 */
const getLesson = createSelector(
  [ getWorkflow, getTabs, getWfModules, getModules, getSelectedWfModule, getLessonData ],
  (workflow, tabs, wfModules, modules, selectedWfModule, lessonData) => {
    if (lessonData === null) {
      return {
        activeSectionIndex: null,
        activeStepIndex: null,
        testHighlight: testLessonHighlightButThereIsNoLesson
      }
    }

    const stateWithHelpers = new StateWithHelpers({
      workflow,
      tabs,
      wfModules,
      modules,
      selected_wf_module: selectedWfModule
    })
    const { activeSectionIndex, activeStepIndex, activeStep } = calculateActiveStep(stateWithHelpers, lessonData.sections)
    const lessonHighlight = activeStep ? activeStep.highlight : []
    const testHighlight = (test) => matchLessonHighlight(lessonHighlight, test)

    return {
      activeSectionIndex,
      activeStepIndex,
      testHighlight
    }
  })
export default getLesson
