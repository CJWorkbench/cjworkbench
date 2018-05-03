import React from 'react'

export default class LessonNav extends React.Component {
  constructor(props) {
    super(props)

    this.onClickPrevious = () => { // Todo upgrade to non-ctor syntax
      this.props.setActiveSectionIndex(Math.max(0, this.props.activeSectionIndex - 1))
    }
    this.onClickNext = () => {
      this.props.setActiveSectionIndex(Math.min(this.props.activeSectionIndex + 1, this.props.nSections - 1))
    }
  }

  render() {
    const i = this.props.activeSectionIndex
    const n = this.props.nSections

    return (
      <footer className="lesson-nav">
        <button
          name="previous"
          disabled={i <= 0}
          onClick={this.onClickPrevious}
          >Previous</button>
        <span className="active">
          <span className="current">{i + 1}</span>
          <span> of </span>
          <span className="total">{n}</span>
        </span>
        <button
          name="next"
          disabled={i + 1 >= n}
          onClick={this.onClickNext}
          >Next</button>
      </footer>
    )
  }
}
