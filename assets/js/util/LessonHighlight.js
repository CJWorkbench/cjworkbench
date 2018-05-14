import PropTypes from 'prop-types'
import deepEqual from 'fast-deep-equal'

const P = PropTypes

function Shape(type, propTypes) {
  return P.shape(Object.assign(
    { type: P.oneOf([ type ]).isRequired }, // hack: only allow the exact given type
    propTypes
  )).isRequired
}

const LessonHighlightType = P.oneOfType([
  Shape('MlModule', {
    name: P.string.isRequired,
  }),
  Shape('WfModule', {
    moduleName: P.string.isRequired,
  }),
  Shape('WfParameter', {
    moduleName: P.string.isRequired,
    name: P.string.isRequired,
  }),
  Shape('WfModuleContextButton', {
    moduleName: P.string.isRequired,
    button: P.oneOf([ 'notes', 'collapse' ]).isRequired,
  }),
  Shape('EditableNotes', {
  }),
  Shape('ModuleSearch', {
  }),
])

/**
 * PropTypes Shape of lesson highlights.
 *
 * Use it in your PropTypes like this:
 *
 * ```js
 * MyComponent.PropTypes = {
 *   lessonHighlights: LessonHighlightsType.isRequired,
 * }
 * ```
 */
export const LessonHighlightsType = P.arrayOf(LessonHighlightType)

/**
 * Test that `lessonHighlight` specifies `test` should be highlighted.
 *
 * For instance:
 *
 * ```js
 * // What we're saying we want to highlight
 * // (e.g., from redux store)
 * const lessonHighlight = [
 *   { type: 'WfModule', name: 'Add from URL' },
 *   { type: 'ModuleSearch' },
 * ]
 *
 * // What we're rendering
 * // (e.g., within ModuleSearch.js)
 * const test = { type: 'ModuleSearch' }
 *
 * matchLessonHighlight(lessonHighlight, test) // true
 * ```
 *
 * @param {Array} lessonHighlight LessonHighlightsType (Array)
 * @param {Object} test Single element that may or may not be in `lessonHighlight`
 */
export const matchLessonHighlight = (lessonHighlight, test) => {
  return lessonHighlight.some(x => deepEqual(x, test))
}

/**
 * Curried matchLessonHighlight(): saves a couple lines of code in
 * parameter-free highlights.
 *
 * ```js
 * const store = {
 *   lesson_highlight: [
 *     { type: 'WfModule', name: 'Add from URL' },
 *     { type: 'ModuleSearch' },
 *   ],
 *   // ...
 * }
 *
 * // What we're rendering
 * // (e.g., within ModuleSearch.js)
 * const isLessonHighlight = stateHasLessonHighlight({ type: 'ModuleSearch' })
 * const mapToProps = (state) => {
 *   isLessonHighlight: isLessonHighlight(state),
 * }
 * ```
 *
 * @param {Object} test Single element that may or may not be in `lessonHighlight`
 * @return {Function} function that accepts `state` as input and outputs whether
 *                    `state` decrees `test` should be highlighted.
 */
export const stateHasLessonHighlight = (test) => {
  if (process.env.NODE_ENV !== 'production') {
    // Make displayName unique. Otherwise, React will hide repeated errors
    // ... which is nondeterministic and breaks unit tests
    const displayName = 'stateHasLessonHighlight' + Math.floor(99999999 * Math.random())
    PropTypes.checkPropTypes(
      { arg: LessonHighlightType.isRequired },
      { arg: test },
      'test',
      displayName
    )
  }

  return (state) => {
    const lessonHighlight = state.lesson_highlight || []
    return matchLessonHighlight(lessonHighlight, test)
  }
}
