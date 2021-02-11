import PropTypes from 'prop-types'

export default function ReportHeader ({ title }) {
  return (
    <header className='report-header'>
      <h1>{title}</h1>
    </header>
  )
}
ReportHeader.propTypes = {
  title: PropTypes.string.isRequired
}
