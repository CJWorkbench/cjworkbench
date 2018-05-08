import React from 'react'
import PropTypes from 'prop-types'
import LessonStep from './LessonStep'
import { LessonHighlightsType } from '../util/LessonHighlight'

export default class LessonSection extends React.Component {
  render() {
    const { active, title, html, steps } = this.props
    const stepComponents = steps.length == 0 ? null : (
      <div className="instructions t-white">
        <h3 className="instructions">Instructions</h3>
        <ol className="steps lesson-content--1">{steps.map(s => <LessonStep key={s.html} {...s} />)}</ol>
      </div>
    )

    return (
      <section className={ active ? 'active' : 'inactive' }>
        <h2>{title}</h2>
        <div className="description lesson-content--1" dangerouslySetInnerHTML={({__html: html})}></div>
        { stepComponents }
      </section>
    )
  }
}

LessonSection.propTypes = {
  active: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  html: PropTypes.string.isRequired,
  steps: PropTypes.arrayOf(PropTypes.shape({
    html: PropTypes.string.isRequired,
    highlight: LessonHighlightsType.isRequired,
  })).isRequired,
}
