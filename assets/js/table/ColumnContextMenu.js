// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import Popover from 'reactstrap/lib/Popover'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import { sortDirectionNone, sortDirectionAsc, sortDirectionDesc} from './UpdateTableAction'

// Modifiers disabled to prevent menu flipping (occurs even when flip=false)
var dropdownModifiers = {
  preventOverflow: {
    enabled: false
  },
  hide: {
    enabled: false
  }
}

export default class ColumnContextMenu extends React.Component {
  static propTypes = {
    setDropdownAction: PropTypes.func.isRequired,
    columnType: PropTypes.string.isRequired,
    renameColumn: PropTypes.func.isRequired
  }

  state = {
    isOpen: false
  }

  toggle = () => {
    this.setState({ isOpen: !this.state.isOpen })
  }

  dropdownRef = React.createRef()

  // Modules that only need to pass the column name and do not force new modules use setDropdownActionDefault
  setDropdownActionDefault (idName) {
    this.props.setDropdownAction(idName, false, {})
    this.setState({ isOpen: false })
  }

  setDropdownActionForceNew (idName) {
    this.props.setDropdownAction(idName, true, {})
    this.setState({ isOpen: false })
  }

  setSortDirection (direction) {
    let params = {
      'sortType': this.props.columnType,
      'sortDirection': direction
    }
    this.props.setDropdownAction('sort-from-table', false, params)
    this.setState({ isOpen: false })
  }

  renameColumn = (...args) => {
    this.props.renameColumn(...args)
    this.setState({ isOpen: false })
  }

  duplicateColumn = () => this.setDropdownActionDefault('duplicate-column')
  sortAscending = () => this.setSortDirection(sortDirectionAsc)
  sortDescending = () => this.setSortDirection(sortDirectionDesc)
  addNewFilter = () => this.setDropdownActionForceNew('filter')
  extractNumbers = () => this.setDropdownActionDefault('extract-numbers')
  cleanText = () => this.setDropdownActionDefault('clean-text')
  dropColumn = () => this.setDropdownActionDefault('selectcolumns')
  convertDate = () => this.setDropdownActionDefault('convert-date')
  convertText = () => this.setDropdownActionDefault('convert-text')

  render() {
    const { isOpen } = this.state

    /*
     * Render menu in a <Popover>.
     *
     * Why not just a <DropdownMenu>? Because react-data-grid forces a style=
     * property on its headers with overflow:hidden; we can't override it in
     * JavaScript.
     *
     * Why not a <Portal>? Because it's really hard to position.
     *
     * Why not a <Popper>? Because the `isOpen` of <PopoverContent> is nice.
     *
     * Why not <PopoverContent>? Because it doesn't close the menu when clicking
     * elsewhere.
     *
     * We're left with <Popover>, which has click-anywhere-to-close,
     * auto-positioning, and simple `isOpen` semantics.
     *
     * Reactstrap's <Dropdown> and <DropdownToggle> elements do all sorts of
     * funky Popper stuff that we don't need because we're using <Popover>. So
     * just use normal HTML elements with Bootstrap class names.
     */

    return (
      <div className={`context-menu ${isOpen ? 'active' : ''}`} ref={this.dropdownRef}>
        <button name='context-menu' title='Column actions' className='btn btn-secondary context-button' onClick={this.toggle}>
          <i className='icon-caret-down'></i>
        </button>
        {isOpen ? (
          <Popover className='dropdown-popover' target={this.dropdownRef} isOpen toggle={this.toggle} hideArrow placement='bottom-end' boundariesElement={document.body}>
            <div className='dropdown-menu show'>
              <DropdownItem onClick={this.renameColumn} className='rename-column-header' toggle={false}>
                <i className="icon-edit"></i>
                <span>Rename</span>
              </DropdownItem>
              <DropdownItem onClick={this.duplicateColumn} className='duplicate-column' toggle={false}>
                <i className="icon-duplicate"></i>
                <span>Duplicate</span>
              </DropdownItem>
              <DropdownItem divider />
              <DropdownItem onClick={this.sortAscending} className='sort-ascending' toggle={false}>
                <i className="icon-sort-up"></i>
                <span>Sort ascending</span>
              </DropdownItem>
              <DropdownItem onClick={this.sortDescending} className='sort-descending' toggle={false}>
                <i className="icon-sort-down"></i>
                <span>Sort descending</span>
              </DropdownItem>
              <DropdownItem divider />
              <DropdownItem onClick={this.addNewFilter} className='filter-column' toggle={false}>
                <i className="icon-filter"></i>
                <span>Filter</span>
              </DropdownItem>
              <DropdownItem onClick={this.cleanText} className='clean-text' toggle={false}>
                <i className="icon-clean"></i>
                <span>Clean Text</span>
              </DropdownItem>
              <DropdownItem divider />
              <DropdownItem onClick={this.convertDate} className='convert-date' toggle={false}>
                <i className="icon-calendar"></i>
                <span>Convert to date & time</span>
              </DropdownItem>
              <DropdownItem onClick={this.extractNumbers} className='extract-numbers' toggle={false}>
                <i className="icon-number"></i>
                <span>Convert to numbers</span>
              </DropdownItem>
              <DropdownItem onClick={this.convertText} className='convert-text' toggle={false}>
                <i className="icon-text"></i>
                <span>Convert to text</span>
              </DropdownItem>
              <DropdownItem divider />
              <DropdownItem onClick={this.dropColumn} className='drop-column' toggle={false}>
                <i className="icon-removec"></i>
                <span>Delete column</span>
              </DropdownItem>
            </div>
          </Popover>
        ) : null}
      </div>
    )
  }
}
