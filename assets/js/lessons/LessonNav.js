import React from 'react'
import PropTypes from 'prop-types'

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
          className="previous action-button button-white"
          disabled={i <= 0}
          onClick={this.onClickPrevious}
          >Previous</button>
        <div className="active t-white content-2">
          <span className="current">{i + 1}</span>
          <span> of </span>
          <span className="total">{n}</span>
        </div>
        <button
          className="next action-button button-white"
          disabled={i + 1 >= n}
          onClick={this.onClickNext}
          >Next</button>
      </footer>
    )
  }
}

LessonNav.propTypes = {
  activeSectionIndex: PropTypes.number.isRequired,
  nSections: PropTypes.number.isRequired,
  setActiveSectionIndex: PropTypes.func.isRequired,
}
