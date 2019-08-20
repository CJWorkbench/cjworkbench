import React from 'react'
import PropTypes from 'prop-types'
import Tab from './Tab'
import * as propTypes from '../propTypes'

export default class TabList extends React.PureComponent {
  static propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      isPending: PropTypes.bool // or undefined
    }).isRequired).isRequired,
    selectedPane: propTypes.selectedPane.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    setName: PropTypes.func.isRequired, // func(tabSlug, name) => undefined
    destroy: PropTypes.func.isRequired, // func(tabSlug) => undefined
    duplicate: PropTypes.func.isRequired, // func(tabSlug) => undefined
    select: PropTypes.func.isRequired, // func(tabSlug) => undefined
    setOrder: PropTypes.func.isRequired // func(tabSlugs) => undefined
  }

  state = {
    dragging: null // { fromIndex, toIndex } of dragging state, or `null` if not dragging
  }

  handleDragStart = (index) => {
    this.setState({ dragging: { fromIndex: index, toIndex: index } })
  }

  handleDragHoverIndex = (index) => {
    const { dragging } = this.state
    if (dragging === null) return

    const { fromIndex, toIndex } = dragging

    if (index !== toIndex) {
      this.setState({
        dragging: {
          fromIndex,
          toIndex: index
        }
      })
    }
  }

  handleDragEnd = () => {
    this.setState({ dragging: null })
  }

  handleDragLeave = () => {
    const { dragging } = this.state
    if (dragging === null) return

    const { fromIndex } = dragging
    this.setState({
      dragging: {
        fromIndex,
        toIndex: fromIndex
      }
    })
  }

  handleDrop = () => {
    const { setOrder, tabs } = this.props
    const { dragging } = this.state
    if (!dragging) return

    const { fromIndex, toIndex } = dragging
    if (fromIndex !== toIndex) {
      const tabSlugs = tabs.map(t => t.slug)
      const fromId = tabSlugs[fromIndex]
      tabSlugs.splice(fromIndex, 1)
      tabSlugs.splice(toIndex > fromIndex ? toIndex - 1 : toIndex, 0, fromId)
      setOrder(tabSlugs)
    }
  }

  render () {
    const { tabs, selectedPane, isReadOnly, setName, select, destroy, duplicate } = this.props
    const { dragging } = this.state

    return (
      <ul
        className={dragging ? 'dragging' : ''}
        onDragLeave={this.handleDragLeave}
      >
        {tabs.map(({ slug, name, isPending }, index) => (
          <Tab
            key={slug}
            index={index}
            slug={slug}
            isPending={isPending}
            isReadOnly={isReadOnly}
            isSelected={selectedPane.pane === 'tab' && selectedPane.tabSlug === slug}
            name={name}
            setName={setName}
            destroy={destroy}
            duplicate={duplicate}
            select={select}
            dragging={dragging}
            onDragStart={this.handleDragStart}
            onDragEnd={this.handleDragEnd}
            onDragHoverIndex={this.handleDragHoverIndex}
            onDrop={this.handleDrop}
          />
        ))}
      </ul>
    )
  }
}
