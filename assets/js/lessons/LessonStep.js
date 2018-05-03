import React from 'react'
import PropTypes from 'prop-types'

export default class LessonStep extends React.Component {
  render() {
    const { html } = this.props

    return (
      <li>
        <div className="description" dangerouslySetInnerHTML={({__html: html})}></div>
      </li>
    )
  }
}

LessonStep.propTypes = {
  html: PropTypes.string.isRequired,
}
