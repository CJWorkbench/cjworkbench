import React from 'react'
import PropTypes from 'prop-types'
import LessonStep from './LessonStep'
import { LessonHighlightsType } from '../util/LessonHighlight'
import { connect } from 'react-redux'

export class LessonSection extends React.PureComponent {
  constructor(props) {
    super(props)

    this.state = {
      activeStepIndex: 0,
    }
  }

  componentDidMount() {
    this.scheduleRefreshActiveStepIndex()
  }

  componentDidUpdate() {
    this.scheduleRefreshActiveStepIndex()
  }

  scheduleRefreshActiveStepIndex() {
    // What we want to do: update this.state.activeStepIndex by running each
    // LessonStep's HTML-embedded `data-test`.
    //
    // When we want to do it: it's complicated. Our lessons are written to test
    // the DOM -- using `document` as a global variable. So we want to test
    // whenever the DOM changes in a substantive way. We assume that only
    // happens when the store changes. But React "batches" updates, meaning
    // the store changes happen _before_ the DOM gets updated. So we'll run
    // our tests on the tick _after_ the DOM gets updated.
    setTimeout(() => this.refreshActiveStepIndex(), 0)
  }

  calculateActiveStepIndex() {
    const steps = this.props.steps
    for (let index = 0; index < steps.length; index++) {
      const step = this.props.steps[index]

      // Parse function; use "!!(...)" syntax to accept anything truthy.
      // Canonical example: `testJs === "document.querySelector('.blah')"`
      // should return true if ".blah" is in the DOM.
      const fn = Function('document', `return !!(${step.testJs})`)
      // Give our function a name: makes it easy to debug crashes
      Object.defineProperty(fn, 'name', {
        value: `LessonSection "${this.props.title}" Step ${index}`,
        writable: false,
      })
      if (!fn(document)) {
        console.log('First unfinished step: ', fn.toString())
        return index // we have completed all steps up to this one
      }
    }

    return null // all steps are complete
  }

  refreshActiveStepIndex() {
    const activeStepIndex = this.calculateActiveStepIndex()
    this.setState({
      activeStepIndex,
    })
  }

  renderStep(step, index) {
    let status
    if (this.state.activeStepIndex !== null && this.state.activeStepIndex < index) {
      status = LessonStep.Status.FUTURE
    } else if (this.state.activeStepIndex === index) {
      status = LessonStep.Status.CURRENT
    } else {
      status = LessonStep.Status.DONE
    }

    console.log(status, this.state, index)

    return (
      <LessonStep key={index} html={step.html} status={status} />
    )
  }

  renderSteps(steps) {
    if (steps.length === 0) {
      return null
    } else {
      return (
        <div className="instructions t-white">
          <h3 className="instructions">Instructions</h3>
          <ol className="steps lesson-content--1">
            {steps.map((s, i) => this.renderStep(s, i))}
          </ol>
        </div>
      )
    }
  }

  render() {
    const { active, title, html, steps } = this.props

    return (
      <section className={ active ? 'active' : 'inactive' }>
        <h2>{title}</h2>
        <div className="description lesson-content--1" dangerouslySetInnerHTML={({__html: html})}></div>
        { this.renderSteps(steps) }
      </section>
    )
  }
}

LessonSection.propTypes = {
  active: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  html: PropTypes.string.isRequired,
  steps: PropTypes.arrayOf(PropTypes.shape({
    html: PropTypes.string.isRequired,
    highlight: LessonHighlightsType.isRequired,
    testJs: PropTypes.string.isRequired,
  })).isRequired,
}

function buildMapStateToProps() {
  // We want our props to change whenever the state changes -- or at least,
  // whenever _some_ properties in the state change. So we need to remember
  // prevState.
  //
  // And how do we make the props change? By setting a monotonically-increasing
  // integer.
  //
  // Here's what'll happen:
  //
  // 1. User clicks
  // 2. Action dispatched
  // 3. mapStateToProps() called; it increments version, changing props
  // 4. LessonSection.render() is called
  // 5. componentDidUpdate() is called, possibly updating state.activeSectionIndex
  // 6. if state updates, LessonSection.render() is called again
  let prevState = {}
  let version = 0

  // Ignore state changes when they're for keys that certainly won't affect
  // our lesson.
  const IgnoredKeys = [ 'lesson_highlight' ]

  return function mapStateToProps(nextState) {
    for (const key of Object.keys(nextState)) {
      // Ignore keys that certainly don't 
      if (IgnoredKeys.includes(key)) continue

      if (nextState[key] !== prevState[key]) {
        version += 1
        break
      }
    }

    prevState = nextState
    return {
      stateVersion: version,
    }
  }
}

export default connect(buildMapStateToProps())(LessonSection)
