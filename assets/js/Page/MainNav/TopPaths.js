import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import LinkLi from './LinkLi'

export default function TopPaths (props) {
  const { currentPath } = props

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
        title={t({ id: 'js.Page.MainNav.examples.title', message: 'Templates' })}
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
          <LinkLi
            href='/courses/en/intro-to-data-journalism'
            isOpen={/^\/courses/.test(currentPath)}
            title={t({ id: 'js.Page.MainNav.intro-to-data-journalism.title', message: 'Intro to Data Journalism' })}
          />
        </ul>
      </LinkLi>
    </ul>
  )
}
TopPaths.propTypes = {
  currentPath: PropTypes.string.isRequired
}
