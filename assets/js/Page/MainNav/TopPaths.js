import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import LinkLi from './LinkLi'

export default function TopPaths (props) {
  const { courses = [], currentPath } = props

  const isLessonsOpen = /^\/(?:lessons|courses)/.test(currentPath)

  return (
    <ul>
      <LinkLi
        href='/workflows'
        isOpen={currentPath === '/workflows'}
        title={t({ id: 'js.Page.MainNav.workflows.title', message: 'My workflows' })}
      />
      <LinkLi
        href='/workflows/shared-with-me'
        isOpen={currentPath === '/workflows/shared-with-me'}
        title={t({ id: 'js.Page.MainNav.workflows-shared-with-me.title', message: 'Shared with me' })}
      />
      <LinkLi
        href='/workflows/examples'
        isOpen={currentPath === '/workflows/examples'}
        title={t({ id: 'js.Page.MainNav.examples.title', message: 'Example workflows' })}
      />
      <LinkLi
        href='/lessons'
        isOpen={isLessonsOpen}
        title={t({ id: 'js.Page.MainNav.training.title', message: 'Training' })}
      >
        <ul>
          <LinkLi
            href='/lessons'
            isOpen={/^\/lessons/.test(currentPath)}
            title={t({ id: 'js.Page.MainNav.lessons.title', message: 'Tutorials' })}
          />
          {courses.map(({ href, title }) => (
            <LinkLi
              key={href}
              href={href}
              isOpen={currentPath.startsWith(href)}
              title={title}
            />
          ))}
        </ul>
      </LinkLi>
    </ul>
  )
}
TopPaths.propTypes = {
  courses: PropTypes.arrayOf(
    PropTypes.shape({
      href: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired
    }).isRequired
  ), // or null, for now
  currentPath: PropTypes.string.isRequired
}
