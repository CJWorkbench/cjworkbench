import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import { Manager as PopperManager, Reference as PopperReference, Popper, Arrow } from 'react-popper'

const PopperModifiers = {
  preventOverflow: {
    boundariesElement: 'viewport'
  }
}

class SearchResultDescription extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired
  }

  render () {
    const { name, description } = this.props

    return (
      <Popper placement='right' modifiers={PopperModifiers}>
        {({ ref, style, placement, arrowProps }) => ReactDOM.createPortal((
          <div
            className={`popover show bs-popover-${placement} module-search-result`}
            ref={ref}
            style={style}
            data-placement={placement}
          >
            <div className='arrow' {...arrowProps} />
            <h3 className='popover-header'>{name}</h3>
            <div className='popover-body'>{description}</div>
          </div>
        ), document.body)}
      </Popper>
    )
  }
}

export default class SearchResult extends React.PureComponent {
  static propTypes = {
    isActive: PropTypes.bool.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    idName: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired, // func(idName) => undefined
    onMouseEnter: PropTypes.func.isRequired, // func(idName) => undefined
  }

  onClick = () => {
    this.props.onClick(this.props.idName)
  }

  onMouseEnter = () => {
    this.props.onMouseEnter(this.props.idName)
  }

  render() {
    const { idName, isActive, isLessonHighlight, isMatch, name, icon, description } = this.props

    const elId = `module-search-result-${idName}`

    const className = [ 'module-search-result' ]
    if (isLessonHighlight) className.push('lesson-highlight')

    return (
      <PopperManager tag={false}>
        <PopperReference>
          {({ ref }) => (
            <li className={className.join(' ')} id={elId} data-module-name={name} onClick={this.onClick} onMouseEnter={this.onMouseEnter} ref={ref}>
              <i className={'icon-' + icon}></i>
              <span className='name'>{name}</span>
            </li>
          )}
        </PopperReference>
        {isActive ? <SearchResultDescription name={name} description={description} /> : null}
      </PopperManager>
    )
  }
}
