import { useReducer } from 'react'
import PropTypes from 'prop-types'
import MainNavHeader from './MainNavHeader'
import TopPaths from './TopPaths'
import UserPaths from './UserPaths'

export default function MainNavFragment (props) {
  const { courses, currentPath, user } = props
  const [open, toggleOpen] = useReducer(open => !open, false)

  return (
    <>
      <MainNavHeader
        href={currentPath === '/workflows' ? null : '/workflows'}
        onToggleOpen={toggleOpen}
      />
      <div className={`details${open ? ' open' : ''}`}>
        <TopPaths courses={courses} currentPath={currentPath} />
        <UserPaths user={user} currentPath={currentPath} />
      </div>
    </>
  )
}
MainNavFragment.propTypes = {
  currentPath: PropTypes.string.isRequired,
  courses: PropTypes.array, // or null, for now
  user: PropTypes.object // or null
}
