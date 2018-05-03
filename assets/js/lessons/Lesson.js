import React from 'react'
import PropTypes from 'prop-types'
import LessonSection from './LessonSection'
import LessonNav from './LessonNav'

export default class Lesson extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      activeSectionIndex: 0,
    }

    this.setActiveSectionIndex = (wantedIndex) => { // TODO upgrade and use newer JSX syntax 'handle... = () => ...'
      this.setState({
        activeSectionIndex: Math.max(Math.min(wantedIndex, this.props.sections.length - 1), 0),
      })
    }
  }

  render() {
    const { header, sections } = this.props

    const sectionComponents = sections.map((s, i) => {
      return <LessonSection
        key={i}
        active={this.state.activeSectionIndex === i}
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
          activeSectionIndex={this.state.activeSectionIndex}
          setActiveSectionIndex={this.setActiveSectionIndex}
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
}
