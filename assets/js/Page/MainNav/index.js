import PropTypes from 'prop-types'
import MainNavFragment from './MainNavFragment'

export default function MainNav (props) {
  const { courses, currentPath, user } = props

  return (
    <nav className='main-nav'>
      <MainNavFragment
        courses={courses}
        currentPath={currentPath}
        user={user}
      />
    </nav>
  )
}
MainNav.propTypes = {
  currentPath: PropTypes.string.isRequired,
  courses: PropTypes.array, // or null, for now
  user: PropTypes.object // or null
}
