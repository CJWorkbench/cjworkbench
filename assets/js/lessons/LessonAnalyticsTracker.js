import React from 'react'
import PropTypes from 'prop-types'

/**
 * A "renderless" container that tracks how far the user has gotten through
 * the lesson.
 */
export default class LessonAnalyticsTracker extends React.PureComponent {
  constructor(props) {
    super(props)

    this.state = {
      maxSectionIndex: -1,
      maxStepIndex: -1,
    }
  }

  componentDidMount() {
    this.track()
  }

  componentDidUpdate() {
    this.track()
  }

  track() {
    if (this.state.maxSectionIndex === null) return // we're already done

    const slug = this.props.slug
    const send = this.props.trackMaxProgress

    if (this.props.activeSectionIndex === null) {
      this.setState({
        maxSectionIndex: null,
        maxStepIndex: null,
      })
      send(slug, null, null)
    } else if (this.props.activeSectionIndex > this.state.maxSectionIndex) {
      this.setState({
        maxSectionIndex: this.props.activeSectionIndex,
        maxStepIndex: this.props.activeStepIndex,
      })
      const sectionTitle = this.props.sections[this.props.activeSectionIndex].title
      send(slug, sectionTitle, this.props.activeStepIndex)
    } else if (this.props.activeSectionIndex === this.state.maxSectionIndex) {
      if (this.props.activeStepIndex > this.state.maxStepIndex) {
        this.setState({
          maxStepIndex: this.props.activeStepIndex,
        })
        const sectionTitle = this.props.sections[this.props.activeSectionIndex].title
        send(slug, sectionTitle, this.props.activeStepIndex)
      }
    }
  }

  render() {
    return null
  }
}

LessonAnalyticsTracker.propTypes = {
  slug: PropTypes.string.isRequired,
  sections: PropTypes.arrayOf(PropTypes.shape({
    title: PropTypes.string.isRequired,
  })).isRequired,
  activeSectionIndex: PropTypes.number, // or null
  activeStepIndex: PropTypes.number, // or null
  trackMaxProgress: PropTypes.func.isRequired, // trackMaxProgress(slug, sectionTitle, step); nulls for done
}
