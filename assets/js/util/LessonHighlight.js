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
