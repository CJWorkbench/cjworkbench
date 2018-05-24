import React from 'react';
import { Dropdown, DropdownMenu, DropdownToggle } from 'reactstrap';
import { downloadPNG, downloadSVG, downloadJSON } from './exportUtils';
var ChartExport = require("chartbuilder/src/js/components/ChartExport");

export default class ExportChart extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            dropdownOpen: false
        };
        this.toggle = this.toggle.bind(this);
        this.exportSvg = this.exportSvg.bind(this);
        this.exportPng = this.exportPng.bind(this);
    }

    toggle() {
        this.setState({
            dropdownOpen: !this.state.dropdownOpen
        });
    }

    exportSvg() {
      downloadSVG(this.props.targetSvgWrapperClassname);
    }

    exportPng() {
      downloadPNG(this.props.targetSvgWrapperClassname);
    }

    render() {
        return (
              <Dropdown isOpen={this.state.dropdownOpen} toggle={this.toggle}>
                <DropdownToggle
                  tag="div"
                  className="export-button btn icon-download"
                  onClick={this.toggle}
                  data-toggle=""
                  aria-expanded={this.state.dropdownOpen}
                >
                </DropdownToggle>
                <div className='button-wrapper'>
                  <DropdownMenu className={this.state.dropdownOpen ? 'show' : ''} left>
                      <div className='dropdown-menu-item' onClick={this.exportSvg}>
                        <span className='t-d-gray content-3 ml-3'>SVG</span>
                      </div>
                      <div className='dropdown-menu-item' onClick={this.exportPng}>
                        <span className='t-d-gray content-3 ml-3'>PNG</span>
                      </div>
                  </DropdownMenu>
                </div>
              </Dropdown>

        )
    }
}
