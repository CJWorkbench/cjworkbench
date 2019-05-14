import PropTypes from 'prop-types'

export const WfModule = PropTypes.shape({
  id: PropTypes.number.isRequired,
  deltaId: PropTypes.number.isRequired
})

export const Tab = PropTypes.shape({
  name: PropTypes.string.isRequired,
  slug: PropTypes.string.isRequired,
  wfModules: PropTypes.arrayOf(WfModule.isRequired).isRequired
})
