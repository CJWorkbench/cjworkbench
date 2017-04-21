// A menu to select a module addition
import React from 'react';
import { ButtonDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap';

export default class ModuleMenu extends React.Component {
  constructor(props) {
    super(props);

    this.toggle = this.toggle.bind(this);
    this.itemClick = this.itemClick.bind(this);

    this.state = {
      dropdownOpen: false,
      items: []
    };
  }

  componentDidMount() {
    var _this = this;
    fetch('/api/modules/', { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        _this.setState({dropdownOpen: this.state.dropdownOpen, items: json}) })
  }

  toggle() {
    this.setState({
      dropdownOpen: !this.state.dropdownOpen
    });
  }

  itemClick(evt) {
    var itemID = evt.target.getAttribute('data-id');
    this.props.addModule(itemID);
    this.setState( { open: false});
  }

  render() {
    return (
      <ButtonDropdown isOpen={this.state.dropdownOpen} toggle={this.toggle}>
        <DropdownToggle caret>
          Add Module
        </DropdownToggle>
        <DropdownMenu>
          {this.state.items.map(
            item => {return <DropdownItem key={item.id} data-id={item.id} onClick={this.itemClick}> {item.name} </DropdownItem>;})
          }
        </DropdownMenu>
      </ButtonDropdown>
    );
  }
}

ModuleMenu.propTypes = {
  addModule:  React.PropTypes.func,
};
