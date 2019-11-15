import React from 'react'
import PropTypes from 'prop-types'
import { Manager, Reference } from 'react-popper'
import Popup from './Popup'
import { Trans } from '@lingui/macro'

export default class Button extends React.PureComponent {
  static propTypes = {
    tabSlug: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired,
    className: PropTypes.string.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    isLastAddButton: PropTypes.bool.isRequired
  }

  state = {
    isOpen: false
  }

  handleClick = () => {
    this.setState({ isOpen: true })
  }

  handleClosePopup = () => {
    this.setState({ isOpen: false })
  }

  render () {
    const { className, index, tabSlug, isLessonHighlight, isLastAddButton } = this.props
    const { isOpen } = this.state

    const buttonClassNames = ['search']
    if (isOpen) buttonClassNames.push('active')
    if (isLessonHighlight) buttonClassNames.push('lesson-highlight')

    return (
      <Manager>
        <Reference>
          {({ ref }) => (
            <div ref={ref} className={className}>
              <button type='button' className={buttonClassNames.join(' ')} onClick={this.handleClick}>
                <i className='icon-add' />{' '}
                <span><Trans id='js.WorkflowEditor.ModuleSearch.Button.addStep' description='This should be all-caps for styling reasons'>ADD STEP</Trans></span>
              </button>
            </div>
          )}
        </Reference>
        {isOpen ? (
          <Popup
            isLastAddButton={isLastAddButton}
            index={index}
            tabSlug={tabSlug}
            onClose={this.handleClosePopup}
          />
        ) : null}
      </Manager>
    )
  }
}
