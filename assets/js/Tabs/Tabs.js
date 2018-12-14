import React from 'react'
import PropTypes from 'prop-types'
import Tab from './Tab'
import NewTabPrompt from './NewTabPrompt'

export default class Tabs extends React.PureComponent {
  static propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired
    }).isRequired).isRequired,
    selectedTabPosition: PropTypes.number.isRequired,
    nPendingCreates: PropTypes.number.isRequired,
    create: PropTypes.func.isRequired, // func(position, name) => undefined
    setName: PropTypes.func.isRequired, // func(tabId, name) => undefined
    destroy: PropTypes.func.isRequired, // func(tabId) => undefined
    select: PropTypes.func.isRequired, // func(tabId) => undefined
  }

  create = () => {
    this.props.create(this.props.tabs.length, '')
  }

  render () {
    const { tabs, selectedTabPosition, nPendingCreates, setName, select, destroy } = this.props

    return (
      <div className='tabs'>
        <ul>
          {tabs.map(({ id, name }, index) => (
            <Tab
              key={id}
              index={index}
              id={id}
              isSelected={selectedTabPosition === index}
              name={name}
              setName={setName}
              destroy={destroy}
              select={select}
            />
          ))}
          <NewTabPrompt
            nPendingCreates={nPendingCreates}
            create={this.create}
          />
        </ul>
      </div>
    )
  }
}
