// Display of output from currently selected module

import React from 'react'
import PropTypes from 'prop-types'
import TableView from './TableView'
import OutputIframe from './OutputIframe'
import debounce from 'debounce'
import { connect } from 'react-redux'
import { findParamValByIdName} from './utils'
import { sortDirectionNone } from './UpdateTableAction'

export class OutputPane extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflowId: PropTypes.number.isRequired,
    lastRelevantDeltaId: PropTypes.number.isRequired,
    selectedWfModuleId: PropTypes.number,
    isPublic: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    showColumnLetter: PropTypes.bool.isRequired,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number,
    htmlOutput: PropTypes.bool
  }

  constructor(props) {
    super(props);

    this.state = {
        leftOffset: 0,
        initLeftOffset: 0,
        width: "100%",
        height: "100%",
        maxWidth: "300%",
        pctBase: null,
        resizing: false
    }

    this.parentBase = React.createRef()

    this.setBusySpinner = this.setBusySpinner.bind(this);
    this.saveSpinnerEl = this.saveSpinnerEl.bind(this);
    this.resizePaneStart = this.resizePaneStart.bind(this);
    this.resizePane = this.resizePane.bind(this);
    this.resizePaneEnd = this.resizePaneEnd.bind(this);

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
    window.addEventListener("resize", debounce(() => { this.setResizePaneRelativeDimensions() }, 200));
    this.setResizePaneRelativeDimensions();
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

  /**
   * Set the width and left offset of the resize pane.
   *
   * Re-position and resize right pane to new relative position with new
   * maximum width relative to window size while maintaining the same
   * visual offset from the left edge.
   */
  setResizePaneRelativeDimensions = () => {
      let resetWidth;
      let resetOffset;
      let maxWidthOffset = 0;
      let resetMaxWidth;

      maxWidthOffset = 100;

      resetOffset = this.state.leftOffset;

      const parentBase = this.parentBase.current;
      const parentWidth = parentBase ? parentBase.width : 100;

      if (resetOffset > 0 || this.state.leftOffset === 0) {
          resetOffset = 0;
          resetWidth = '100%';
      } else {
          resetWidth = ((parentWidth - resetOffset) / parentWidth) * 100 + '%';
      }

      resetMaxWidth = ((this.getWindowWidth() - maxWidthOffset) / parentWidth) * 100 + '%';

      if (parentBase && parseFloat(resetWidth) > parseFloat(resetMaxWidth)) {
          resetOffset = resetOffset + ( parentWidth * ( ( parseFloat(resetWidth) - parseFloat(resetMaxWidth) ) / 100 ) );
          resetWidth = resetMaxWidth;
      }

      this.setState({
          leftOffset : resetOffset,
          initLeftOffset: resetOffset,
          width: resetWidth,
          height: "100%",
          maxWidth: resetMaxWidth,
          pctBase: parentWidth,
      });
  }

  render() {
    const { isReadOnly, isPublic, sortColumn, sortDirection, showColumnLetter, lastRelevantDeltaId } = this.props

    // Make a table component even if no module ID (should still show an empty table)
    var tableView =
      <TableView
        selectedWfModuleId={this.props.selectedWfModuleId}
        lastRelevantDeltaId={lastRelevantDeltaId}
        resizing={this.state.resizing}
        api={this.props.api}
        setBusySpinner={this.setBusySpinner}
        isReadOnly={isReadOnly}
        sortColumn={sortColumn}
        sortDirection={sortDirection}
        showColumnLetter={showColumnLetter}
      />

    // This iframe holds the module HTML output, e.g. a visualization
    var outputIFrame = null;
    if (this.props.htmlOutput) {
      outputIFrame = <OutputIframe
          selectedWfModuleId={this.props.selectedWfModuleId}
          workflowId={this.props.workflowId}
          isPublic={isPublic}
          lastRelevantDeltaId={lastRelevantDeltaId}
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
      <div
        className={"outputpane" + (this.props.focus ? " focus" : "")}
        ref={this.parentBase}
        onClick={this.props.setFocus}
      >
        {spinner}
        {outputIFrame}
        {tableView}
      </div>
    )
  }
}

function mapStateToProps(state, ownProps) {
  const { workflow, wfModules, modules } = state
  const selectedWfModuleId = workflow.wf_modules[state.selected_wf_module || 0] || null
  const selectedWfModule = wfModules[String(selectedWfModuleId)] || null
  const selectedModule = modules[String(selectedWfModule ? selectedWfModule.module_version.module : null)] || null
  const id_name = selectedModule ? selectedModule.id_name : null

  const showColumnLetter = id_name === 'formula' || id_name === 'reorder-columns'

  let sortColumn = null
  let sortDirection = sortDirectionNone

  if (id_name === 'sort-from-table') {
    const columnParam = findParamValByIdName(selectedWfModule, 'column');
    const directionParam = findParamValByIdName(selectedWfModule, 'direction').value;

    sortColumn = columnParam && columnParam.value || null
    sortDirection = directionParam || sortDirectionNone
  }

  return {
    workflowId: workflow.id,
    lastRelevantDeltaId: selectedWfModule ? selectedWfModule.last_relevant_delta_id : null,
    selectedWfModuleId,
    isPublic: workflow.public,
    isReadOnly: workflow.read_only,
    htmlOutput: selectedWfModule ? selectedWfModule.html_output : false,
    showColumnLetter,
    sortColumn,
    sortDirection,
  }
}

export default connect(
  mapStateToProps
)(OutputPane)
