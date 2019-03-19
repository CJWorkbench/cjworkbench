import React from 'react'
import WfHamburgerMenu from '../WfHamburgerMenu'

function getActiveSection () {
  return window.location.pathname.startsWith('/workflows') ? 'workflows' : 'lessons'
}

function propsForLink (activeSection, name) {
  if (name === activeSection) {
    return { href: null, className: 'active' }
  } else {
    return { href: `/${name}`, className: 'inactive' }
  }
}

export default class Navbar extends React.Component {
  render() {
    const activeSection = getActiveSection()

    return (
      <div>
        <nav className="navbar">
          <div className="logo">
            <img src={`${window.STATIC_URL}images/logo.svg`} className="logo"/>
            <img src={`${window.STATIC_URL}images/logo-text.svg`} className="logo-text"/>
          </div>
          <div className="links">
            <a {...propsForLink(activeSection, 'workflows')}>WORKFLOWS</a>
            <a {...propsForLink(activeSection, 'lessons')}>TRAINING</a>
          </div>
          <WfHamburgerMenu />
        </nav>
      </div>
    )
  }
}
