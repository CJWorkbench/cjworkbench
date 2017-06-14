import React from 'react';
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap';

import { csrfToken } from './utils'


export default class ImportModuleFromGitHub extends React.Component {
  constructor(props) {
    super(props);
    this.state = {url: ''};

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
  }

  handleChange(event) {
    this.setState({url: event.target.value});
  }

  handleSubmit(event) {
      var url = '/api/importfromgithub/';
      var eventData = {'url': this.state.url};
      fetch(url, {
        method: 'post',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(eventData)
      });
  }

  render() {
    return (
      <form onSubmit={this.handleSubmit}>
        <label>
          &nbsp; Import module from GitHub: &nbsp;
          <input type="text" value={this.state.value} onChange={this.handleChange} />
        </label>
        <input type="submit" value="Import" />
      </form>
    );
  }
}


ImportModuleFromGitHub.propTypes = {
  url:  React.PropTypes.string,
};

