import PropTypes from 'prop-types'

export const selectedPane = PropTypes.oneOfType([
  PropTypes.exact({
    pane: PropTypes.oneOf(['tab']).isRequired,
    tabSlug: PropTypes.string.isRequired
  }),
  PropTypes.exact({
    pane: PropTypes.oneOf(['report', 'dataset']).isRequired
  })
])
