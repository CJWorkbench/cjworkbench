import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import detectOverflow from '@popperjs/core/lib/utils/detectOverflow.js'
import { Popper } from 'react-popper'
import { connect } from 'react-redux'
import lessonSelector from '../../lessons/lessonSelector'
import { ModulePropType } from './PropTypes'
import Prompt from './Prompt'
import SearchResults from './SearchResults'
import { addModuleAction } from '../../workflow-reducer'
import { PopperSameWidth } from '../../components/PopperHelpers'

const KeyCodes = {
  Tab: 9
}

/**
 * This Popper stuff requires a _manual_ test suite. Editing? Get testing!
 *
 * TEST: DROPDOWN RESIZES
 *
 * 1. Open a workflow with a few steps
 * 2. Click the _very first_ add-step slot
 *    -- popup should open below slot, with scrollbar
 * 3. Type "xx"
 *    -- as you type, popup should shrink; search field should stay in same
 *       spot.
 * 4. Ctrl-Backspace
 *    -- back to what we saw at step 2
 *
 * TEST: DROPUP RESIZES
 *
 * 1. Open a workflow with a few modules
 * 2. Click an "add-step" slot near the bottom of the page
 *    -- popup should open, with scrollbar; search field should be where it
 *       would have been had we gotten a dropdown instead of a dropup
 * 3. Type "xx"
 *    -- as you type, popup should shrink; search field should stay in same
 *       spot.
 * 4. Ctrl-Backspace
 *    -- back to what we saw at step 2
 *
 * TEST*2: SAME THINGS, WITH 'ADD STEP' BUTTON
 * -- with both dropdown and dropup, the search field should appear exactly on
 *    where the 'ADD STEP' button is -- not below it.
 *
 * TEST: SCROLL SEARCH RESULTS
 *
 * 1. Open a workflow
 * 2. Click "add step"
 *    -- popup should open
 * 3. Scroll through the popup
 *    -- you should see a scrollbar; scrolling should affect the scrollbar.
 *
 * TEST: SCROLL MODULE STACK SO BUTTON IS OFFSCREEN
 *
 * 1. Open a workflow with a few modules
 * 2. Click a middle add-step slot
 *    -- popup appears
 * 3. Scroll all the way up and down in the step stack (_outside_ the
 *    step-search popup).
 *    -- popup should not affect the page size. (It should be pinned within the
 *       page.)
 *
 * TEST: CLICK OFF MODULE SEARCH SHOULD CLOSE IT
 *
 * 1. Open a workflow
 * 2. Click add-step
 *    -- popup should appear
 * 3. Click the table
 *    -- popup should disappear
 *
 * TEST: CLICK ON MODULE SHOULD ADD IT
 *
 * 1. Open a workflow
 * 2. Click add-step
 *    -- popup should appear
 * 3. Click a step
 *    -- popup should disappear and step should be added
 */

const PopperFlipBasedOnScrollPosition = {
  // Override Popper's 'flip' modifier: flip if we're low on the page.
  // (Normally, Popper flips if the popper won't fit in the wanted direction.
  // But _our_ popup is enormous -- taller than the page -- so it only fits
  // after the user has typed some letters. We don't want user-types-letters
  // to cause a flip, so we mustn't use the height of the popup to determine
  // whether to flip.)
  name: 'flip',
  fn: ({ state, options, name }) => {
    const refBox = state.rects.reference
    const refCenterY = refBox.y + (refBox.height / 2)
    const boundingEl = state.elements.reference.offsetParent.offsetParent
    const boundingBox = boundingEl.getBoundingClientRect()
    // If prompt is past the 60% mark on the page, open upwards.
    // otherwise, open downwards.
    const midY = boundingBox.y + (boundingBox.height * 0.6)
    const placement = refCenterY > midY ? 'top' : 'bottom'
    if (placement !== state.placement) {
      state.modifiersData[name]._skip = true
      state.placement = placement
      state.reset = true
    }
  }
}

const PopperOffsetFormBelowReference = {
  name: 'offset',
  fn: ({ state, name }) => {
    let y = 0
    if (state.placement === 'top') {
      const formHeight = state.elements.popper.querySelector('form').clientHeight
      y = formHeight + state.rects.reference.height
    }

    if (state.modifiersData.popperOffsets !== null) {
      state.modifiersData.popperOffsets.y += y
    }
    state.modifiersData[name] = {
      top: { x: 0, y }, // this is the only offset we might add
      left: { x: 0, y: 0 },
      right: { x: 0, y: 0 },
      bottom: { x: 0, y: 0 }
    }
  }
}

const PopperOffsetToCoverReference = {
  name: 'offset',
  fn: ({ state, name }) => {
    // Center the form atop the reference.
    const formHeight = state.elements.popper.querySelector('form').clientHeight
    const refHeight = state.rects.reference.height
    // formTopOverflow: number of pixels form top is higher than reference top
    const formTopOverflow = (formHeight - state.rects.reference.height) / 2
    // Through luck of math, y is the same whether placement is top or bottom
    const y = -refHeight - formTopOverflow

    if (state.modifiersData.popperOffsets !== null) {
      state.modifiersData.popperOffsets.y += state.placement === 'top' ? -y : y
    }
    state.modifiersData[name] = {
      top: { x: 0, y: state.placement === 'top' ? -y : 0 },
      left: { x: 0, y: 0 },
      right: { x: 0, y: 0 },
      bottom: { x: 0, y: state.placement === 'bottom' ? y : 0 }
    }
  }
}

const PopperMaxHeight = {
  // https://github.com/atomiks/popper.js/blob/0558a222de782687ec217847ea2f1be839b9dbb3/src/modifiers/maxSize.js
  name: 'maxSize',
  enabled: true,
  phase: 'main',
  requiresIfExists: ['offset', 'preventOverflow', 'flip'],
  options: {
    padding: 5
  },
  fn: ({ state, name, options }) => {
    const overflow = detectOverflow(state, options)
    // detectOverflow() neglects modifiersData
    const y = state.modifiersData.preventOverflow ? state.modifiersData.preventOverflow.y : 0
    const { height } = state.rects.popper

    // maxHeight = height - (overflow-top if placing above, overflow-bottom if placing below)
    let maxHeight = height - overflow[state.placement] - y

    // Clamp maxHeight to handle the case:
    //
    // 1. Open a popup
    // 2. Scroll around
    //
    // Expected results: the menu doesn't get enormous
    maxHeight = Math.min(maxHeight, window.innerHeight * 0.7)

    state.modifiersData[name] = { maxHeight }
  }
}

const PopperApplyMaxHeight = {
  name: 'applyMaxSize',
  enabled: true,
  phase: 'beforeWrite',
  requires: ['maxSize'],
  fn: ({ state }) => {
    const { maxHeight } = state.modifiersData[PopperMaxHeight.name]
    state.styles.popper.maxHeight = `${maxHeight}px`
  }
}

const PopperPreventOverflowKeepPopperOnscreen = {
  // Used instead of preventOverflow. The goal is to force the popup
  // to remain on-screen, even if the reference scrolls away.
  //
  // This is very similar to preventOverflow with options
  // * mainAxis: true
  // * altAxis: false
  // * boundary: 'clippingParents'
  // ... but unlike @popperjs/core method, _this_ preventOverflow won't
  // move the popper onto the reference element. (Normally, since the
  // reference element is huge, it would.)
  name: 'preventOverflow',
  options: { boundary: 'clippingParents', padding: 5, altBoundary: true },
  fn: ({ state, options, name }) => {
    const overflow = detectOverflow(state, { ...options, altBoundary: true })
    const popperOffsets = state.modifiersData.popperOffsets

    const offset = popperOffsets.y

    const preventedOffset = state.placement === 'top'
      ? Math.min(offset, offset - overflow.bottom)
      : Math.max(offset, offset + overflow.top)

    popperOffsets.y = preventedOffset
    state.modifiersData[name] = { x: 0, y: preventedOffset - offset }
  }
}

const PopperModifiers = [
  PopperSameWidth,
  PopperPreventOverflowKeepPopperOnscreen,
  PopperFlipBasedOnScrollPosition, // replaces 'flip'
  { name: 'hide', enabled: false }, // show, even when too tall
  PopperOffsetFormBelowReference,
  PopperMaxHeight,
  PopperApplyMaxHeight
]

const PopperModifiersLastButton = [...PopperModifiers, PopperOffsetToCoverReference]

export class Popup extends React.PureComponent {
  static propTypes = {
    tabSlug: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
    onClose: PropTypes.func.isRequired, // func() => undefined
    addModule: PropTypes.func.isRequired, // func(tabSlug, index, moduleIdName) => undefined
    onUpdate: PropTypes.func // func() => undefined -- for Popper.scheduleUpdate()
  }

  state = {
    search: ''
  }

  handleChangeSearchInput = (value) => {
    this.setState({ search: value })
  }

  componentDidUpdate () {
    // Resize Popper.
    if (this.props.onUpdate) this.props.onUpdate()
  }

  handleClickModule = (moduleIdName) => {
    const { tabSlug, index, addModule, onClose } = this.props
    addModule(tabSlug, index, moduleIdName)
    onClose()
  }

  render () {
    const { modules, isLessonHighlight, onClose } = this.props
    const { search } = this.state

    const classNames = ['module-search-popup']
    if (isLessonHighlight) classNames.push('lesson-highlight')

    return (
      <div className={classNames.join(' ')}>
        <Prompt cancel={onClose} onChange={this.handleChangeSearchInput} value={search} />
        <SearchResults search={search} modules={modules} onClickModule={this.handleClickModule} />
      </div>
    )
  }
}

export class PopperPopup extends React.PureComponent {
  static propTypes = {
    tabSlug: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired,
    isLastAddButton: PropTypes.bool.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
    onClose: PropTypes.func.isRequired, // func() => undefined
    addModule: PropTypes.func.isRequired // func(tabSlug, index, moduleIdName) => undefined
  }

  containerRef = React.createRef()

  componentDidMount () {
    ['click', 'touchstart', 'keyup'].forEach(eventName =>
      document.addEventListener(eventName, this.onClickDocument, true)
    )
  }

  componentWillUnmount () {
    ['click', 'touchstart', 'keyup'].forEach(eventName =>
      document.removeEventListener(eventName, this.onClickDocument, true)
    )
  }

  onClickDocument = (ev) => {
    const container = this.containerRef.current
    if (!container) return

    // Copy/paste from Reactstrap src/Dropdown.js
    if (ev && (ev.which === 3 || (ev.type === 'keyup' && ev.which !== KeyCodes.Tab))) return

    if (container.contains(ev.target) && container !== ev.target && (ev.type !== 'keyup' || ev.which === KeyCodes.Tab)) {
      return
    }

    this.props.onClose()
  }

  render () {
    const { isLastAddButton } = this.props

    // We render <div.module-search-popper> for positioning and
    // <div.module-search-popup> for onClickDocument. They both need a ref.
    // Popper's un-React16-like "ref" usage inspires us to use two different
    // refs for the same behavior.
    return ReactDOM.createPortal((
      <Popper modifiers={isLastAddButton ? PopperModifiersLastButton : PopperModifiers}>
        {({ ref, style, placement, scheduleUpdate }) => (
          <div
            ref={ref}
            style={style}
            data-placement={placement}
            className='module-search-popper'
          >
            <div className='click-outside-listener' ref={this.containerRef}>
              <Popup onUpdate={scheduleUpdate} {...this.props} />
            </div>
          </div>
        )}
      </Popper>
    ), document.body)
  }
}

const mapStateToProps = (state, ownProps) => {
  const { testHighlight } = lessonSelector(state)
  return {
    isLessonHighlight: testHighlight({ type: 'Module', id_name: null, index: ownProps.index }),
    modules: Object.values(state.modules)
      .filter(m => m.uses_data)
      .filter(m => !m.deprecated)
      .map(module => {
        return {
          idName: module.id_name,
          isLessonHighlight: testHighlight({ type: 'Module', id_name: module.id_name, index: ownProps.index }),
          name: module.name,
          description: module.description,
          category: module.category,
          icon: module.icon
        }
      })
  }
}

const mapDispatchToProps = (dispatch) => {
  return {
    addModule (tabSlug, index, moduleIdName) {
      const action = addModuleAction(moduleIdName, { tabSlug, index }, {})
      dispatch(action)
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(PopperPopup)
