import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import PopperUtils from 'popper.js/dist/umd/popper-utils'
import { Popper } from 'react-popper'
import { connect } from 'react-redux'
import lessonSelector from '../../lessons/lessonSelector'
import { ModulePropType } from './PropTypes'
import Prompt from './Prompt'
import SearchResults from './SearchResults'
import { addModuleAction } from '../../workflow-reducer'

const KeyCodes = {
  Tab: 9
}

/**
 * This Popper stuff requires a _manual_ test suite. Editing? Get testing!
 *
 * TEST: DROPDOWN RESIZES
 *
 * 1. Open a workflow with a few modules
 * 2. Click the _very first_ add-module slot
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
 * 2. Click an "add-module" slot near the bottom of the page
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
 * 2. Click "add module"
 *    -- popup should open
 * 3. Scroll through the popup
 *    -- you should see a scrollbar; scrolling should affect the scrollbar.
 *
 * TEST: SCROLL MODULE STACK SO BUTTON IS OFFSCREEN
 *
 * 1. Open a workflow with a few modules
 * 2. Click a middle add-module slot
 *    -- popup appears
 * 3. Scroll all the way up and down in the module stack (_outside_ the
 *    module-search popup).
 *    -- popup should not affect the page size. (It should be pinned within the
 *       page.)
 *
 * TEST: CLICK OFF MODULE SEARCH SHOULD CLOSE IT
 *
 * 1. Open a workflow
 * 2. Click add-module
 *    -- popup should appear
 * 3. Click the table
 *    -- popup should disappear
 *
 * TEST: CLICK ON MODULE SHOULD ADD IT
 *
 * 1. Open a workflow
 * 2. Click add-module
 *    -- popup should appear
 * 3. Click a module
 *    -- popup should disappear and module should be added
 */
const PopperModifiers = {
  autoPopperWidth: {
    enabled: true,
    order: 1,
    fn: (data) => {
      // Modify in-place, for speed (we're called often)
      data.styles.width = data.offsets.reference.width
      return data
    }
  },

  flip: { enabled: false }, // autoPopperPlacement replaces this
  hide: { enabled: false }, // show, always
  autoPopperPlacement: {
    enabled: true,
    order: 2,
    fn: (data) => {
      const refBox = data.offsets.reference
      const refCenterY = (refBox.top + refBox.bottom) / 2

      // If prompt is past the 60% mark on the page, open upwards.
      // otherwise, open downwards.
      const flipped = refCenterY > window.innerHeight * 0.6
      data.flipped = flipped
      data.placement = flipped ? 'top' : 'bottom'

      return data
    }
  },

  autoPopperHeight: {
    enabled: true,
    order: 3,
    padding: 10,
    fn: (data, { padding }) => {
      // Place the prompt below the "Add Step" button
      // (visually, place the prompt where the to-be-added module will go.)
      const refBottom = data.offsets.reference.bottom

      let maxHeight
      if (data.placement === 'bottom') {
        maxHeight = Math.floor(
          window.innerHeight -
          padding -
          refBottom
        )
      } else {
        // since prompt is below and we're placing above, promptHeight doesn't
        // actually cost any space and doesn't factor in to maxHeight.
        const promptHeight = data.instance.popper.querySelector('form').getBoundingClientRect().height
        maxHeight = Math.floor(
          refBottom -
          padding +
          promptHeight
        )
      }

      // Clamp maxHeight to handle the case:
      //
      // 1. Open a popup
      // 2. Scroll around
      //
      // Expected results: the menu doesn't get enormous
      maxHeight = Math.min(maxHeight, window.innerHeight * 0.7)

      data.styles.maxHeight = maxHeight
      data.instance.popper.style.maxHeight = maxHeight // so we can getPopperOffsets()
      data.offsets.popper = PopperUtils.getPopperOffsets(
        data.instance.popper,
        data.offsets.reference,
        data.placement
      )
      return data
    }
  },

  offset: { enabled: false },
  shiftOffset: {
    enabled: true,
    order: 201, // after 'offset', which calculated the desired position
    fn: (data) => {
      // Place the prompt below the "Add Step" button
      // (visually, place the prompt where the to-be-added module will go.)
      const { placement, instance, offsets: { popper, reference } } = data
      const promptHeight = instance.popper.querySelector('form').getBoundingClientRect().height

      if (placement === 'top') {
        const shift = reference.height + promptHeight
        popper.top += shift
        popper.bottom += shift
      } // else placement === 'bottom' and Popper default is what we want
      return data
    }
  },

  preventOverflow: {
    // autoPopperHeight sets maxHeight, which ought to prevent overflow; but
    // there's still the case where the user scrolls the module stack such that
    // the reference <button> is off the page. Use Popper's normal
    // preventOverflow+hide to lock the popup onto the page.
    boundariesElement: 'viewport'
  }
}
const PopperModifiersLastButton = {
  ...PopperModifiers,
  autoPopperHeight: {
    ...PopperModifiers.autoPopperHeight,
    fn: (data, { padding }) => {
      // Vertically center the prompt over the "Add Step" button
      const refBox = data.offsets.reference
      const refCenterY = (refBox.top + refBox.bottom) / 2

      // shiftOffset will vertically center the prompt over its reference element.
      const promptHeight = data.instance.popper.querySelector('form').getBoundingClientRect().height

      let maxHeight
      if (data.placement === 'bottom') {
        maxHeight = (
          window.innerHeight -
          padding -
          Math.floor(refCenterY - promptHeight / 2)
        )
      } else {
        maxHeight = (
          Math.floor(refCenterY + promptHeight / 2) -
          padding
        )
      }

      // Clamp maxHeight to handle the case:
      //
      // 1. Open a popup
      // 2. Scroll around
      //
      // Expected results: the menu doesn't get enormous
      maxHeight = Math.min(maxHeight, window.innerHeight * 0.7)

      data.styles.maxHeight = maxHeight
      data.instance.popper.style.maxHeight = maxHeight // so we can getPopperOffsets()
      data.offsets.popper = PopperUtils.getPopperOffsets(
        data.instance.popper,
        data.offsets.reference,
        data.placement
      )
      return data
    }
  },

  shiftOffset: {
    ...PopperModifiers.shiftOffset,
    fn: (data) => {
      // Vertically center the prompt over the "Add Step" button
      const { placement, instance, offsets: { popper, reference } } = data
      const promptHeight = instance.popper.querySelector('form').getBoundingClientRect().height
      const refHeight = reference.height
      const offset = (promptHeight + refHeight) / 2
      const mult = placement === 'bottom' ? -1 : 1
      popper.top += mult * offset
      return data
    }
  }
}

export class Popup extends React.PureComponent {
  static propTypes = {
    tabSlug: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
    close: PropTypes.func.isRequired, // func() => undefined
    addModule: PropTypes.func.isRequired, // func(tabSlug, index, moduleIdName) => undefined
    onUpdate: PropTypes.func // func() => undefined -- for Popper.scheduleUpdate()
  }

  state = {
    search: ''
  }

  onSearchInputChange = (value) => {
    this.setState({ search: value })
  }

  componentDidUpdate () {
    // Resize Popper.
    //
    // Another place this might make sense is componentDidUpdate(). But
    this.props.onUpdate()
  }

  onClickModule = (moduleIdName) => {
    const { tabSlug, index, addModule, close } = this.props
    addModule(tabSlug, index, moduleIdName)
    close()
  }

  render () {
    const { modules, isLessonHighlight, close } = this.props
    const { search } = this.state

    const classNames = ['module-search-popup']
    if (isLessonHighlight) classNames.push('lesson-highlight')

    return (
      <div className={classNames.join(' ')}>
        <Prompt cancel={close} onChange={this.onSearchInputChange} value={search} />
        <SearchResults search={search} modules={modules} onClickModule={this.onClickModule} />
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
    close: PropTypes.func.isRequired, // func() => undefined
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

    this.props.close()
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
    isLessonHighlight: testHighlight({ type: 'Module', name: null, index: ownProps.index }),
    modules: Object.values(state.modules)
      .filter(m => m.uses_data)
      .filter(m => !m.deprecated)
      .map(module => {
        return {
          idName: module.id_name,
          isLessonHighlight: testHighlight({ type: 'Module', name: module.name, index: ownProps.index }),
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
