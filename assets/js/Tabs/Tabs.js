import React from 'react'
import PropTypes from 'prop-types'
import Tab from './Tab'
import PendingTab from './PendingTab'
import NewTabPrompt from './NewTabPrompt'

export default class Tabs extends React.PureComponent {
  static propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired
    }).isRequired).isRequired,
    selectedTabPosition: PropTypes.number.isRequired,
    pendingTabNames: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    create: PropTypes.func.isRequired, // func(position, name) => undefined
    setName: PropTypes.func.isRequired, // func(tabId, name) => undefined
    destroy: PropTypes.func.isRequired, // func(tabId) => undefined
    select: PropTypes.func.isRequired, // func(tabId) => undefined
  }

  create = () => {
    this.props.create(this.props.tabs.length, '')
  }

  render () {
    const { tabs, selectedTabPosition, pendingTabNames, setName, select, destroy } = this.props

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
        </ul>
        {pendingTabNames.length > 0 ? (
          <ul className='pending'>
            {pendingTabNames.map((name, index) => (
              <PendingTab
                key={index}
                name={name}
              />
            ))}
          </ul>
        ) : null}
        <NewTabPrompt
          create={this.create}
        />
      </div>
    )
  }
}
