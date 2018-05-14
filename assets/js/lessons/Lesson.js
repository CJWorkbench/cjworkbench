import React from 'react'
import PropTypes from 'prop-types'
import LessonSection from './LessonSection'
import LessonNav from './LessonNav'
import { setLessonHighlight } from '../workflow-reducer'
import { connect } from 'react-redux'
import { LessonHighlightsType } from '../util/LessonHighlight'

export class Lesson extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      activeSectionIndex: 0,
    }

    this.setActiveSectionIndex = (wantedIndex) => { // TODO upgrade and use newer JSX syntax 'handle... = () => ...'
      const activeSectionIndex = Math.max(Math.min(wantedIndex, this.props.sections.length - 1), 0)
      this.setState({
        activeSectionIndex,
      })
    }
  }

  render() {
    const { header, sections } = this.props

    const sectionComponents = sections.map((s, i) => {
      return <LessonSection
        key={i}
        active={this.state.activeSectionIndex === i}
        setLessonHighlight={this.props.setLessonHighlight}
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
      highlight: LessonHighlightsType.isRequired,
      testJs: PropTypes.string.isRequired,
    })).isRequired,
  })).isRequired,
  setLessonHighlight: PropTypes.func.isRequired,
}

const mapStateToProps = (state) => {
  return {}
}

const mapDispatchToProps = (dispatch) => {
  return {
    setLessonHighlight: (...args) => dispatch(setLessonHighlight(...args)),
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(Lesson)
