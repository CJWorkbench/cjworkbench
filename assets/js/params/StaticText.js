import PropTypes from 'prop-types'

export default function StaticText ({ label }) {
  return <div className='static-text'>{label}</div>
}
StaticText.propTypes = {
  name: PropTypes.string.isRequired
}
