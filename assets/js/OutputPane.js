// Display of output from currently selected module

import React from 'react'
import TableView from './TableView'
import PropTypes from 'prop-types'
import { OutputIframe } from './OutputIframe'
import Resizable from 're-resizable'
import debounce from 'lodash/debounce'

export default class OutputPane extends React.Component {

  constructor(props) {
    super(props);

    this.state = {
        leftOffset : 0,
        initLeftOffset: 0,
        width: "100%",
        height: "100%",
        maxWidth: "300%",
        parentBase: null,
        pctBase: null,
        resizing: false
    };

    this.setBusySpinner = this.setBusySpinner.bind(this);
    this.saveSpinnerEl = this.saveSpinnerEl.bind(this);
    this.resizePaneStart = this.resizePaneStart.bind(this);
    this.resizePane = this.resizePane.bind(this);
    this.resizePaneEnd = this.resizePaneEnd.bind(this);
    this.setResizePaneRelativeDimensions = this.setResizePaneRelativeDimensions.bind(this);

    this.spinnerEl = null;
    this.spinning = false;
  }

  // Spinner state did not work as part of component state, conditionally visible in render()
  // It didn't appear when refreshing a large table. My guess is that is because React updates are batched,
  // the spinner on and spinner off updates are combined and we never see it when the table re-render is long.
  // So, now we turn the spinner on and off immediately through direct DOM styling
  setBusySpinner(visible) {
    if (this.spinnerEl && visible != this.spinning) {
      this.spinnerEl.style.display = visible ? 'flex' : 'none';
      this.spinning = visible;
    }
  }

  // Can't do this as an anonymous function like ref={ (el) => {this.spinnerEl=el} }
  // because el will sometimes be null if we do. See https://reactjs.org/docs/refs-and-the-dom.html#caveats
  saveSpinnerEl(el) {
    this.spinnerEl = el;
  }

  componentDidMount() {
    window.addEventListener("resize", debounce(() => { this.setResizePaneRelativeDimensions(this.props.libraryOpen) }, 200));
    this.setResizePaneRelativeDimensions(this.props.libraryOpen);
  }

  componentWillReceiveProps(nextProps) {
      console.log("OutputPane props");
      console.log(nextProps);
    if (nextProps.libraryOpen !== this.props.libraryOpen) {
        this.setResizePaneRelativeDimensions(nextProps.libraryOpen, true);
    }
  }

  getWindowWidth() {
      return window.innerWidth
        || document.documentElement.clientWidth
        || document.body.clientWidth;
  }

  resizePaneStart() {
      this.props.setOverlapping(true);
      this.props.setFocus();
  }

  resizePane(e, direction, ref, d) {
    let offset = this.state.initLeftOffset - d.width;
    this.setState({
        leftOffset: offset,
        resizing: true
    });
  }

  resizePaneEnd(e, direction, ref, d) {
      // We set percentage width so that we can maintain the outer layout of the module stack and output pane
      // while still allowing the right pane to stretch beyond its boundaries. Setting a pixel width on the inner
      // part of the output pane expands the outer frame, distorting the layout of the entire page.
      let width = parseFloat(this.state.width) + ((d.width / this.state.pctBase) * 100) + '%';
      this.setState({
          initLeftOffset: this.state.leftOffset,
          width,
          resizing: false
      });
      this.props.setOverlapping((this.state.leftOffset < 0));
  }

  /* Set the width and left offset of the resize pane relative to the window size and collapsed state of the
        module library. Deals with the following cases:

  1. Window resize -- re-position and resize right pane to new relative position with new maximum width relative to
        window size while maintaining the same visual offset from the left edge

  2. Open/close module library while right pane is at "0" -- re-position and resize right pane to "0" position relative
        to ML state

  3. Open/close module library while right pane is expanded but less than max: re-position and resize right pane so
        it maintains the same visual position on the screen

  4. Open module library while right pane is at max width relative to closed ML: re-position and re-size right pane to
        max width relative to open ML position
   */

  setResizePaneRelativeDimensions(libraryState, libraryToggle) {
      let libraryOffset = 0;
      let resetWidth;
      let resetOffset;
      let maxWidthOffset = 0;
      let resetMaxWidth;

      if (libraryState === true) {
          maxWidthOffset = 240;
          if (libraryToggle === true) {
              libraryOffset = -140;
          }
      }

      if (libraryState === false) {
          maxWidthOffset = 100;
          if (libraryToggle === true) {
              libraryOffset = 140;
          }

      }

      resetOffset = this.state.leftOffset + libraryOffset;

      if (resetOffset > 0 || this.state.leftOffset === 0) {
          resetOffset = 0;
          resetWidth = '100%';
      } else {
          resetWidth = ((this.state.parentBase.clientWidth - resetOffset) / this.state.parentBase.clientWidth) * 100 + '%';
      }

      resetMaxWidth = ((this.getWindowWidth() - maxWidthOffset) / this.state.parentBase.clientWidth) * 100 + '%';

      if ( parseFloat(resetWidth) > parseFloat(resetMaxWidth) ) {
          resetOffset = resetOffset + ( this.state.parentBase.clientWidth * ( ( parseFloat(resetWidth) - parseFloat(resetMaxWidth) ) / 100 ) );
          resetWidth = resetMaxWidth;
      }

      this.setState({
          leftOffset : resetOffset,
          initLeftOffset: resetOffset,
          width: resetWidth,
          height: "100%",
          maxWidth: resetMaxWidth,
          pctBase: this.state.parentBase.clientWidth
      });
  }

  findCurrentModuleInWorkflow(wf) {
      console.log(wf);
      var modulesFound = wf.wf_modules.filter((wfm) => {return wfm.id == this.props.selectedWfModuleId});
      console.log(modulesFound);
      return modulesFound.length > 0 ? modulesFound[0] : null;
  }

  render() {
    // We figure out whether we need to indicate sort status here so that we don't have to
    // pass a ton of data to the TableView

    var moduleIsSort = false;
    let currentModule = this.findCurrentModuleInWorkflow(this.props.workflow);
    console.log("OutputPane data:")
      console.log(this.props.workflow);
    console.log(currentModule)
    if(currentModule) {
        moduleIsSort = (currentModule.module_version.module.id_name == "sort-from-table")
    }
    console.log(moduleIsSort)

    // Maps sort direction to ReactDataGrid direction names
    let sortDirectionTranslator = ["NONE", "ASC", "DESC"]

    // Make a table component even if no module ID (should still show an empty table)
    var tableView =
      <TableView
        id={this.props.id}
        revision={this.props.revision}
        resizing={this.state.resizing}
        api={this.props.api}
        setBusySpinner={this.setBusySpinner}
        sortColumn={moduleIsSort ? currentModule.parameter_vals[0].value : undefined}
        sortDirection={moduleIsSort ? sortDirectionTranslator[currentModule.parameter_vals[2].value] : undefined}
      />

    // This iframe holds the module HTML output, e.g. a visualization
    var outputIFrame = null;
    if (this.props.htmlOutput) {
      outputIFrame = <OutputIframe
          api={this.props.api}
          selectedWfModuleId={this.props.selectedWfModuleId}
          workflow={this.props.workflow}
          revision={this.props.revision}
      />
    }

    // Spinner is always rendered, but we toggle 'display: none' in setBusySpinner()
    // Start hidden. TableView will turn it on when needed.
    var spinner =
      <div
        id="spinner-container-transparent"
        style={{display:'none'}}
        ref={ this.saveSpinnerEl }
      >
        <div id="spinner-l1">
          <div id="spinner-l2">
            <div id="spinner-l3"></div>
          </div>
        </div>
      </div>

    return (
        <div className={"outputpane" + (this.props.focus ? " focus" : "")}
             ref={(ref) => this.state.parentBase = ref}
             onClick={this.props.setFocus} >
            <Resizable
              style={{
                  transform: "translateX(" + this.state.leftOffset + "px)"
              }}
              className="outputpane-box"
              enable={{
                  top:false,
                  right:false,
                  bottom:false,
                  left:true,
                  topRight:false,
                  bottomRight:false,
                  bottomLeft:false,
                  topLeft:false
              }}
              size={{
                  width: this.state.width,
                  height: this.state.height,
              }}
              minWidth="100%"
              maxWidth={this.state.maxWidth}
              onResizeStart={this.resizePaneStart}
              onResize={this.resizePane}
              onResizeStop={this.resizePaneEnd}
            >

              {spinner}

              { outputIFrame }

              { tableView }

            </Resizable>
        </div>
    );
  }
}

OutputPane.propTypes = {
  id:                 PropTypes.number,             // can be undefined, if no selected module
  revision:           PropTypes.number.isRequired,
  api:                PropTypes.object.isRequired,
  selectedWfModuleId: PropTypes.number,
  htmlOutput:         PropTypes.bool,
};
