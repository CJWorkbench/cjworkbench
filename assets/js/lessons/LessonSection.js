import React from 'react'
import LessonStep from './LessonStep'

export default class LessonSection extends React.Component {
  render() {
    const { active, title, html, steps } = this.props
    const stepComponents = steps.map(s => <LessonStep key={s.html} {...s} />)

    return (
      <section className={ active ? 'active' : 'inactive' }>
        <h2>{title}</h2>
        <div className="description" dangerouslySetInnerHTML={({__html: html})}></div>
        <h3>Instructions</h3>
        { stepComponents.length ? <ol className="steps">{stepComponents}</ol> : '' }
      </section>
    )
  }
}
