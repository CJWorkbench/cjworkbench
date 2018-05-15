import React from 'react'
import PropTypes from 'prop-types'
import LessonSection from './LessonSection'
import LessonNav from './LessonNav'
import lessonSelector from './lessonSelector'
import { connect } from 'react-redux'
import { LessonHighlightsType } from '../util/LessonHighlight'

export class Lesson extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      // The section the user is reading right now (selected via LessonNav)
      currentSectionIndex: 0,
    }

    this.setCurrentSectionIndex = (index) => { // TODO use nicer React+Babel syntax
      this.setState({ currentSectionIndex: index })
    }
  }

  render() {
    const { header, sections } = this.props

    const sectionComponents = sections.map((s, i) => {
      return <LessonSection
        key={i}
        index={i}
        isCurrent={this.state.currentSectionIndex === i}
        activeSectionIndex={this.props.activeSectionIndex}
        activeStepIndex={this.props.activeStepIndex}
        {...s}
        />
    })

    return (
      <article className="lesson">
        <h1>{header.title}</h1>
        <div className="description" dangerouslySetInnerHTML={({__html: header.html})}></div>
        <div className="sections">{sectionComponents}</div>
        <LessonNav
          nSections={sections.length}
          activeSectionIndex={this.props.activeSectionIndex}
          currentSectionIndex={this.state.currentSectionIndex}
          setCurrentSectionIndex={this.setCurrentSectionIndex}
          />
      </article>
    )
  }
}
Lesson.propTypes = {
  header: PropTypes.shape({
    title: PropTypes.string.isRequired,
    html: PropTypes.string.isRequired,
  }).isRequired,
  sections: PropTypes.arrayOf(PropTypes.shape({
    title: PropTypes.string.isRequired,
    html: PropTypes.string.isRequired,
    steps: PropTypes.arrayOf(PropTypes.shape({
      html: PropTypes.string.isRequired,
    })).isRequired,
  })).isRequired,

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
  activeSectionIndex: PropTypes.number.isRequired,
  activeStepIndex: PropTypes.number.isRequired,
}

const mapStateToProps = (state) => {
  const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
  return { activeSectionIndex, activeStepIndex }
}

export default connect(mapStateToProps)(Lesson)
