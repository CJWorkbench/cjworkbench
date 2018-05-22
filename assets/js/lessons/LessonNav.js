import React from 'react'
import PropTypes from 'prop-types'

export default class LessonNav extends React.PureComponent {
  constructor(props) {
    super(props)

    this.onClickPrevious = () => { // Todo upgrade to non-ctor syntax
      this.props.setCurrentSectionIndex(Math.max(0, this.props.currentSectionIndex - 1))
    }
    this.onClickNext = () => {
      this.props.setCurrentSectionIndex(Math.min(this.props.currentSectionIndex + 1, this.props.nSections - 1))
    }
  }

  render() {
    const i = this.props.currentSectionIndex
    const a = this.props.activeSectionIndex
    const n = this.props.nSections

    return (
      <footer className="lesson-nav">
        <button
          name="Previous"
          className={`previous action-button button-white ${(a !== null && a < i) ? 'lesson-highlight' : ''}`}
          disabled={i <= 0}
          onClick={this.onClickPrevious}
          >Previous</button>
        <div className="current-and-total t-white content-2">
          <span className="current">{i + 1}</span>
          <span> of </span>
          <span className="total">{n}</span>
        </div>
        <button
          name="Next"
          className={`next action-button button-white ${(a !== null && a > i) ? 'lesson-highlight' : ''}`}
          disabled={i + 1 >= n}
          onClick={this.onClickNext}
          >Next</button>
      </footer>
    )
  }
}

LessonNav.propTypes = {
  currentSectionIndex: PropTypes.number.isRequired, // what the user is reading
  activeSectionIndex: PropTypes.number,  // where the next incomplete step is (null if done)
  nSections: PropTypes.number.isRequired,
  setCurrentSectionIndex: PropTypes.func.isRequired,
}
