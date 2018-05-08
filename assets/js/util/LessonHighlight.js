import PropTypes from 'prop-types'
import deepEqual from 'fast-deep-equal'

const P = PropTypes

function Shape(type, propTypes) {
  return P.shape(Object.assign(
    { type: P.oneOf([ type ]).isRequired }, // hack: only allow the exact given type
    propTypes
  )).isRequired
}

export const LessonHighlightType = P.oneOfType([
  Shape('MlModule', {
    name: P.string.isRequired,
  }),
  Shape('WfModule', {
    name: P.string.isRequired,
  }),
  Shape('WfParameter', {
    moduleName: P.string.isRequired,
    name: P.string.isRequired,
  }),
  Shape('WfModuleContextButton', {
    moduleName: P.string.isRequired,
    button: P.oneOf([ 'notes', ]).isRequired,
  }),
  Shape('EditableNotes', {
  }),
  Shape('ModuleSearch', {
  }),
])

export const LessonHighlightsType = P.arrayOf(LessonHighlightType)

export function validLessonHighlight(obj) {
  if (!(obj instanceof Array)) {
    obj = [ obj ]
  }

  if (process.env.NODE_ENV !== 'production') {
    const displayName = 'LessonHighlight' + Math.floor(99999999 * Math.random()) // random name => React never hides logs
    PropTypes.checkPropTypes(
      { elements: LessonHighlightsType.isRequired },
      { elements: obj },
      'element',
      displayName
    )
  }

  return obj
}

export const matchLessonHighlight = (lessonHighlight, test) => {
  return lessonHighlight.some(x => deepEqual(x, test))
}

export const stateHasLessonHighlight = (test) => {
  if (process.env.NODE_ENV !== 'production') {
    const displayName = 'stateHasLessonHighlight' + Math.floor(99999999 * Math.random()) // random name => React never hides logs
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
