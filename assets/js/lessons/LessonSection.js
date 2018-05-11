import React from 'react'
import PropTypes from 'prop-types'
import LessonStep from './LessonStep'
import { LessonHighlightsType } from '../util/LessonHighlight'
import { StateWithHelpers } from './DoneHelpers'
import { connect } from 'react-redux'

export class LessonSection extends React.PureComponent {
  renderStep(step, index) {
    let status
    if (this.props.activeStepIndex !== null && this.props.activeStepIndex < index) {
      status = LessonStep.Status.FUTURE
    } else if (this.props.activeStepIndex === index) {
      status = LessonStep.Status.CURRENT
    } else {
      status = LessonStep.Status.DONE
    }

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

function isStepDone(sectionTitle, stepIndex, stateWithHelpers, step) {
  // Canonical example testJs:
  // `return workflow.selectedWfModule.moduleName === 'Add from URL'`
  const fn = new Function('state', 'workflow', step.testJs)
  // Give our function a name: makes it easy to debug crashes
  Object.defineProperty(fn, 'name', {
    value: `LessonSection "${sectionTitle}" Step ${stepIndex + 1}`,
    writable: false,
  })

  try {
    return fn(stateWithHelpers, stateWithHelpers.workflow)
  } catch (e) {
    console.error(e)
    return false
  }
}

function calculateActiveStepIndex(state, ownProps) {
  const stateWithHelpers = new StateWithHelpers(state)

  // Run each testJs function until one returns false
  for (let stepIndex = 0; stepIndex < ownProps.steps.length; stepIndex++) {
    const step = ownProps.steps[stepIndex]
    if (!isStepDone(ownProps.title, stepIndex, stateWithHelpers, step)) {
      return stepIndex
    }
  }

  return null // all steps complete
}

function mapStateToProps(state, ownProps) {
  return {
    activeStepIndex: calculateActiveStepIndex(state, ownProps),
  }
}

export default connect(mapStateToProps)(LessonSection)
