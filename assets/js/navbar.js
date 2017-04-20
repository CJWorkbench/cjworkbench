// Navbar at top of all logged-in pages.
// May have various elements on different pages, including toolbar

import React from 'react';


export default class NavBar extends React.Component {

  render() {
    return (
      <div className="mb-5">
        <nav className="navbar navbar-toggleable-md  navbar-light bg-faded">
          <h1 className="navbar-brand mb-0">CJ Workbench</h1>
          <a className="nav-link navbar-toggler-right" href="/logout">Logout</a>
        </nav>
      </div>
    );
  }
}

