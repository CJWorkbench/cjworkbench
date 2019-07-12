import React from 'react'
import PropTypes from 'prop-types'
import LessonFooter from './LessonFooter'
import LessonSection from './LessonSection'
import LessonNav from './LessonNav'
import lessonSelector from './lessonSelector'
import { connect } from 'react-redux'

export class Lesson extends React.PureComponent {
  static propTypes = {
    header: PropTypes.shape({
      title: PropTypes.string.isRequired,
      html: PropTypes.string.isRequired
    }).isRequired,
    sections: PropTypes.arrayOf(PropTypes.shape({
      title: PropTypes.string.isRequired,
      html: PropTypes.string.isRequired,
      isFullScreen: PropTypes.bool.isRequired,
      steps: PropTypes.arrayOf(PropTypes.shape({
        html: PropTypes.string.isRequired
      })).isRequired
    })).isRequired,
    footer: PropTypes.shape({
      title: PropTypes.string.isRequired,
      html: PropTypes.string.isRequired,
      isFullScreen: PropTypes.bool.isRequired
    }).isRequired,

    /*
     * activeSectionIndex, activeStepIndex: the step the user needs to
     * complete next in order to finish the lesson.
     *
     * Two examples illustrate why activeSectionIndex != currentSectionIndex:
     *
     * 1. The first section might contain introductory text and no steps. We want
     *    the user to read it anyway.
     * 2. Once a user has completed all steps in a section, we want to _prompt_
     *    to switch sections -- not navigate automatically.
     */
    activeSectionIndex: PropTypes.number, // or null
    activeStepIndex: PropTypes.number // or null
  }

  state = {
    // The section the user is reading right now (selected via LessonNav)
    currentSectionIndex: 0
  }

  setCurrentSectionIndex = (index) => {
    this.setState({ currentSectionIndex: index })
  }

  render () {
    const { header, footer, sections, activeSectionIndex, activeStepIndex } = this.props
    const { currentSectionIndex } = this.state

    const sectionComponents = sections.map((s, i) => {
      return <LessonSection
        key={i}
        index={i}
        isCurrent={currentSectionIndex === i}
        activeSectionIndex={activeSectionIndex}
        activeStepIndex={activeStepIndex}
        {...s}
      />
    })

    const currentSectionOrFooter = sections[currentSectionIndex] || footer
    const isFullScreen = currentSectionOrFooter.isFullScreen
    const classNames = ['lesson']
    if (isFullScreen) classNames.push('fullscreen')

    return (
      <article className={classNames.join(' ')}>
        <h1>{header.title}</h1>
        <div className='description' dangerouslySetInnerHTML={({ __html: header.html })} />
        <div className='sections'>
          <div className='content'>
            {sectionComponents}
          </div>
          <LessonFooter
            key='footer'
            isCurrent={this.state.currentSectionIndex === sections.length}
            isFinished={this.props.activeSectionIndex === null}
            isFullScreen={footer.is_full_screen}
            {...footer}
          />
        </div>
        <LessonNav
          nSections={sections.length}
          activeSectionIndex={activeSectionIndex}
          currentSectionIndex={this.state.currentSectionIndex}
          setCurrentSectionIndex={this.setCurrentSectionIndex}
        />
      </article>
    )
  }
}

const mapStateToProps = (state) => {
  const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
  return { activeSectionIndex, activeStepIndex }
}

export default connect(mapStateToProps)(Lesson)
