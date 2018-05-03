import React from 'react'

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
