import PropTypes from 'prop-types'

export const ModulePropType = PropTypes.shape({
  idName: PropTypes.string.isRequired,
  isLessonHighlight: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  deprecated: PropTypes.object, // or null -- usually null! We don't care about its properties in module search
  category: PropTypes.string.isRequired,
  icon: PropTypes.string.isRequired,
})
