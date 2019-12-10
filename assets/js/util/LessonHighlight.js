import PropTypes from 'prop-types'

const P = PropTypes

function Shape (type, propTypes) {
  return P.shape(Object.assign(
    { type: P.oneOf([type]).isRequired }, // hack: only allow the exact given type
    propTypes
  )).isRequired
}

const LessonHighlightType = P.oneOfType([
  Shape('Module', {
    index: P.number.isRequired, // index in ModuleStack where we want to add the module
    id_name: P.string.isRequired // slug of the Module
  }),
  Shape('WfModule', {
    moduleIdName: P.string.isRequired,
    index: P.number
  }),
  Shape('WfModuleContextButton', {
    moduleIdName: P.string.isRequired,
    button: P.oneOf(['notes', 'collapse']).isRequired,
    index: P.number
  }),
  Shape('EditableNotes', {
  })
])

/**
 * PropTypes Shape of lesson highlights.
 *
 * Use it in your PropTypes like this:
 *
 * ```js
 * MyComponent.propTypes = {
 *   lessonHighlights: LessonHighlightsType.isRequired,
 * }
 * ```
 */
export const LessonHighlightsType = P.arrayOf(LessonHighlightType)

const matchOneLessonHighlight = (lessonHighlight, test) => {
  return !Object.keys(lessonHighlight).some(key => test[key] !== null && test[key] !== lessonHighlight[key])
}

/**
 * Test that `lessonHighlight` specifies `test` should be highlighted.
 *
 * For instance:
 *
 * ```js
 * // What we're saying we want to highlight
 * // (e.g., from redux store)
 * const lessonHighlight = [
 *   { type: 'WfModule', moduleName: 'Add from URL' },
 *   { type: 'Module', name: 'Filter', index: 0 },
 * ]
 *
 * // What we're rendering
 * // (e.g., within WfModule.js)
 * const test = { type: 'WfModule', moduleName: 'Add from URL' }
 *
 * matchLessonHighlight(lessonHighlight, test) // true
 * ```
 *
 * @param {Array} lessonHighlight LessonHighlightsType (Array)
 * @param {Object} test Single element that may or may not be in `lessonHighlight`
 */
export const matchLessonHighlight = (lessonHighlight, test) => {
  return lessonHighlight.some(x => matchOneLessonHighlight(x, test))
}
