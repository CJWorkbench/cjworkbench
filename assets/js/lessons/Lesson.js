import React from 'react'
import LessonSection from './LessonSection'

export default class Lesson extends React.Component {
  render() {
    const { header, sections } = this.props

    const sectionComponents = sections.map(s => <LessonSection key={s.title} {...s} />)

    return (
      <article className="lesson">
        <h1>{header.title}</h1>
        <div className="description" dangerouslySetInnerHTML={({__html: header.html})}></div>
        <div className="sections">{sectionComponents}</div>
      </article>
    )
  }
}
