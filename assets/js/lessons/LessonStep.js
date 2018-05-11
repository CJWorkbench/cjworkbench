import React from 'react'
import PropTypes from 'prop-types'
import { LessonHighlightsType } from '../util/LessonHighlight'

export default class LessonStep extends React.Component {
  render() {
    const { html, status } = this.props

    return (
      <li className={status}>
        <div className="description" dangerouslySetInnerHTML={({__html: html})}></div>
      </li>
    )
  }
}

LessonStep.Status = {
  FUTURE: 'future',
  CURRENT: 'current',
  DONE: 'done',
}

LessonStep.propTypes = {
  html: PropTypes.string.isRequired,
  status: PropTypes.oneOf([
    LessonStep.Status.FUTURE,
    LessonStep.Status.CURRENT,
    LessonStep.Status.DONE,
  ]).isRequired,
}
