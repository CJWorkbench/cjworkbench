import React from 'react'
import PropTypes from 'prop-types'
import Confetti from 'react-dom-confetti'

export default class LessonFooter extends React.PureComponent {
  static propTypes = {
    title: PropTypes.string.isRequired,
    html: PropTypes.string,
    isCurrent: PropTypes.bool.isRequired, // did the user navigate here?
    isFinished: PropTypes.bool.isRequired, // did the user complete everything?
  }

  state = {
    isFinished: false // switches to true, then stays true (for confetti)
  }

  componentDidUpdate (prevProps, prevState) {
    if (prevState.isFinished) return
    if (this.props.isCurrent && this.props.isFinished) {
      this.setState({ isFinished: true })
    }
  }

  render () {
    const { isCurrent, title, html } = this.props
    const { isFinished } = this.state

    return (
      <section className={`lesson-footer ${isCurrent ? 'current' : 'not-current'}`}>
        <a href='/lessons/' className='backToLessons'>Tutorials</a>
        <h2>{title}</h2>
        <div className='description' dangerouslySetInnerHTML={({__html: html})}></div>
        <Confetti active={isFinished} className='confetti' />
      </section>
    )
  }
}
