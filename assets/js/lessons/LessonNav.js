import React from 'react'
import PropTypes from 'prop-types'

export default class LessonNav extends React.PureComponent {
  static propTypes = {
    currentSectionIndex: PropTypes.number.isRequired, // what the user is reading
    activeSectionIndex: PropTypes.number,  // where the next incomplete step is (null if done)
    nSections: PropTypes.number.isRequired,
    setCurrentSectionIndex: PropTypes.func.isRequired,
  }

  onClickPrevious = () => {
    this.props.setCurrentSectionIndex(Math.max(0, this.props.currentSectionIndex - 1))
  }

  onClickNext = () => {
    this.props.setCurrentSectionIndex(Math.min(this.props.currentSectionIndex + 1, this.props.nSections))
  }

  render() {
    const c = this.props.currentSectionIndex
    const n = this.props.nSections
    let a = this.props.activeSectionIndex
    if (a === null) {
      // when all steps are complete, direct user to lesson footer
      a = n
    }

    return (
      <footer className="lesson-nav">
        <button
          name="Previous"
          className={`previous action-button button-white ${a < c ? 'lesson-highlight' : ''}`}
          disabled={c <= 0}
          onClick={this.onClickPrevious}
        >
          Previous
        </button>
        {c === n ? null : (
          <div className="current-and-total">
            <span className="current">{c + 1}</span>
            <span> of </span>
            <span className="total">{n}</span>
          </div>
        )}
        <button
          name="Next"
          className={`next action-button button-white ${a > c ? 'lesson-highlight' : ''}`}
          disabled={c + 1 > n}
          onClick={this.onClickNext}
        >
          Next
        </button>
      </footer>
    )
  }
}
