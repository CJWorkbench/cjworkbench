import React from 'react'
import PropTypes from 'prop-types'
import { Manager, Reference } from 'react-popper'
import Popup from './Popup'

export default class Button extends React.PureComponent {
  static propTypes = {
    tabSlug: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired,
    className: PropTypes.string.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired
  }

  state = {
    isOpen: false
  }

  openSearch = () => {
    this.setState({ isOpen: true })
  }

  closeSearch = () => {
    this.setState({ isOpen: false })
  }

  render () {
    const { className, index, tabSlug, isLessonHighlight } = this.props
    const { isOpen } = this.state

    const buttonClassNames = [ 'search' ]
    if (isLessonHighlight) buttonClassNames.push('lesson-highlight')

    return (
      <Manager>
        <Reference>
          {({ ref }) => (
            <div ref={ref} className={className}>
              <button type='button' className={buttonClassNames.join(' ')} onClick={this.openSearch}>
                <i className="icon-addc"></i>{' '}
                <span>ADD STEP</span>
              </button>
            </div>
          )}
        </Reference>
        {isOpen ? (
          <Popup
            index={index}
            tabSlug={tabSlug}
            close={this.closeSearch}
          />
        ) : null}
      </Manager>
    )
  }
}
