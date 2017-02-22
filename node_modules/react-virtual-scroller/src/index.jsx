'use strict'

import Component from 'react-class'

import React from 'react';
import { findDOMNode } from 'react-dom';

const LoadMask   = require('react-load-mask')
const assign     = require('object-assign')
const DragHelper = require('drag-helper')
const normalize  = require('react-style-normalizer')
const hasTouch   = require('has-touch')

const preventDefault = event => event && event.preventDefault()
const signum         = x => x < 0? -1: 1
const emptyFn        = () => {}
const ABS            = Math.abs

const LoadMaskFactory = React.createFactory(LoadMask)

var horizontalScrollbarStyle = {}

var IS_MAC     = global && global.navigator && global.navigator.appVersion && global.navigator.appVersion.indexOf("Mac") != -1
var IS_FIREFOX = global && global.navigator && global.navigator.userAgent && !!~global.navigator.userAgent.toLowerCase().indexOf('firefox')

if (IS_MAC){
  horizontalScrollbarStyle.position = 'absolute'
  horizontalScrollbarStyle.height   = 20
}

const PT = React.PropTypes
const DISPLAY_NAME = 'Scroller'

const ON_OVERFLOW_NAMES = {
  vertical  : 'onVerticalScrollOverflow',
  horizontal: 'onHorizontalScrollOverflow'
}

const ON_SCROLL_NAMES = {
  vertical  : 'onVerticalScroll',
  horizontal: 'onHorizontalScroll'
}

/**
 * Called on scroll by mouse wheel
 */
const syncScrollbar = function(orientation) {

  return function(scrollPos, event){

    var domNode       = orientation == 'horizontal'? this.getHorizontalScrollbarNode(): this.getVerticalScrollbarNode()
    var scrollPosName = orientation == 'horizontal'? 'scrollLeft': 'scrollTop'
    var overflowCallback

    domNode[scrollPosName] = scrollPos

    var newScrollPos = domNode[scrollPosName]

    if (newScrollPos != scrollPos){
      // overflowCallback = this.props[ON_OVERFLOW_NAMES[orientation]]
      // overflowCallback && overflowCallback(signum(scrollPos), newScrollPos)
    } else {
        preventDefault(event)
    }
  }
}

const syncHorizontalScrollbar = syncScrollbar('horizontal')
const syncVerticalScrollbar   = syncScrollbar('vertical')

const scrollAt = function(orientation){
  var syncFn = orientation == 'horizontal'?
          syncHorizontalScrollbar:
          syncVerticalScrollbar

  return function(scrollPos, event){
      // this.mouseWheelScroll = true

      syncFn.call(this, Math.round(scrollPos), event)

      // raf(function(){
      //     this.mouseWheelScroll = false
      // }.bind(this))
  }
}

const onScroll = function(orientation){

  var clientHeightNames = {
    vertical  : 'clientHeight',
    horizontal: 'clientWidth'
  }

  var scrollHeightNames = {
    vertical  : 'scrollHeight',
    horizontal: 'scrollWidth'
  }

  return function(event){

    var scrollPosName = orientation == 'horizontal'? 'scrollLeft': 'scrollTop'
    var target        = event.target
    var scrollPos     = target[scrollPosName]

    var onScroll   = this.props[ON_SCROLL_NAMES[orientation]]
    var onOverflow = this.props[ON_OVERFLOW_NAMES[orientation]]

      // if (!this.mouseWheelScroll && onOverflow){
      if (onOverflow){
          if (scrollPos == 0){
            onOverflow(-1, scrollPos)
          } else if (scrollPos + target[clientHeightNames[orientation]] >= target[scrollHeightNames[orientation]]){
            onOverflow(1, scrollPos)
          }
      }

      ;(onScroll || emptyFn)(scrollPos)
  }
}

/**
 * The scroller can have a load mask (loadMask prop is true by default),
 * you just need to specify loading=true to see it in action
 *
 * <Scroller loading={true} />
 *
 * If you don't want a load mask, specify
 *
 * <Scroller loadMask={false} />
 *
 * Or if you want to customize the loadMask factory, specify
 *
 * function mask(props) { return aMaskFactory(props) }
 * <Scroller loading={true} loadMask={mask}
 *
 */
class Scroller extends Component {

  render(){
    var props = this.p = this.prepareProps(this.props)

    var loadMask            = this.renderLoadMask(props)
    var horizontalScrollbar = this.renderHorizontalScrollbar(props)
    var verticalScrollbar   = this.renderVerticalScrollbar(props)

    var events = {}

    if (!hasTouch){
      events.onWheel = this.handleWheel
    } else {
      events.onTouchStart = this.handleTouchStart
    }

    //extra div needed for SAFARI V SCROLL
        //maxWidth needed for FF - see
        //http://stackoverflow.com/questions/27424831/firefox-flexbox-overflow
        //http://stackoverflow.com/questions/27472595/firefox-34-ignoring-max-width-for-flexbox
    var content = <div className="z-content-wrapper-fix" style={{maxWidth: 'calc(100% - ' + props.scrollbarSize + 'px)'}}
            children={props.children} />

    var renderProps = this.prepareRenderProps(props)

    return <div {...renderProps}>
      {loadMask}
      <div className="z-content-wrapper" {...events}>
        {content}
        {verticalScrollbar}
      </div>

      {horizontalScrollbar}
    </div>
  }

  prepareRenderProps(props) {
    var renderProps = assign({}, props)

    delete renderProps.height
    delete renderProps.width

    return renderProps
  }

  handleTouchStart(event) {

    var props  = this.props
    var scroll = {
        top : props.scrollTop,
        left: props.scrollLeft
      }

      var newScrollPos
      var side

      DragHelper(event, {
        scope: this,
        onDrag: function(event, config) {
          if (config.diff.top == 0 && config.diff.left == 0){
            return
          }

          if (!side){
            side = ABS(config.diff.top) > ABS(config.diff.left)? 'top': 'left'
          }

          var diff = config.diff[side]

          newScrollPos = scroll[side] - diff

          if (side == 'top'){
            this.verticalScrollAt(newScrollPos, event)
          } else {
            this.horizontalScrollAt(newScrollPos, event)
          }
        }
      })

      event.stopPropagation()
      preventDefault(event)
  }

  handleWheel(event){

    var props = this.props
    // var normalizedEvent = normalizeWheel(event)

    var virtual = props.virtualRendering
    var horizontal = IS_MAC? ABS(event.deltaX) > ABS(event.deltaY): event.shiftKey
    var scrollStep = props.scrollStep
    var minScrollStep = props.minScrollStep

    var scrollTop = props.scrollTop
    var scrollLeft = props.scrollLeft

    // var delta = normalizedEvent.pixelY
    var delta = event.deltaY

    if (horizontal){
      // delta = delta || normalizedEvent.pixelX
      delta = delta || event.deltaX
      minScrollStep = props.minHorizontalScrollStep || minScrollStep
    } else {
      if (delta !== 0){
        minScrollStep = props.minVerticalScrollStep   || minScrollStep
      }
    }

    if (typeof props.interceptWheelScroll == 'function'){
      delta = props.interceptWheelScroll(delta, normalizedEvent, event)
    } else if (minScrollStep){
      if (ABS(delta) < minScrollStep && delta !== 0){
        delta = signum(delta) * minScrollStep
      }
    }

    if (horizontal){
      this.horizontalScrollAt(scrollLeft + delta, event)
      props.preventDefaultHorizontal && preventDefault(event)

    } else {
      if (delta !== 0) {
        this.verticalScrollAt(scrollTop + delta, event)
        props.preventDefaultVertical && preventDefault(event)
      }
    }
  }

  componentWillReceiveProps(){
    setTimeout(this.fixHorizontalScrollbar, 0)
  }

  componentDidMount() {
    this.fixHorizontalScrollbar()

    ;(this.props.onMount || emptyFn)(this);

    setTimeout(function(){
      this.fixHorizontalScrollbar();
    }.bind(this), 0)
  }

  fixHorizontalScrollbar() {

    const thisNode = findDOMNode(this)

    if (!thisNode){
      return
    }

    this.horizontalScrollerNode = this.horizontalScrollerNode || thisNode.querySelector('.z-horizontal-scroller')

    const dom = this.horizontalScrollerNode

    if (dom){
      const height = dom.style.height

      dom.style.height = height == '0.2px'? '0.1px': '0.2px'
    }
  }

  getVerticalScrollbarNode(){
    return this.verticalScrollbarNode = this.verticalScrollbarNode || findDOMNode(this).querySelector('.ref-verticalScrollbar')
  }

  getHorizontalScrollbarNode(){
    return this.horizontalScrollbarNode = this.horizontalScrollbarNode || findDOMNode(this).querySelector('.ref-horizontalScrollbar')
  }

  componentWillUnmount(){
    delete this.horizontalScrollerNode
    delete this.horizontalScrollbarNode
    delete this.verticalScrollbarNode
  }

  ////////////////////////////////////////////////
  //
  // RENDER METHODS
  //
  ////////////////////////////////////////////////
  renderVerticalScrollbar(props) {
    var height = props.scrollHeight
    var verticalScrollbarStyle = {
      width: props.scrollbarSize
    }

    var onScroll = this.onVerticalScroll

    return <div className="z-vertical-scrollbar" style={verticalScrollbarStyle}>
        <div
          className="ref-verticalScrollbar"
          onScroll={onScroll}
          style={{overflow: 'auto', width: '100%', height: '100%'}}
        >
            <div className="z-vertical-scroller" style={{height: height}} />
        </div>
    </div>
  }

  renderHorizontalScrollbar(props) {
    var scrollbar
    var onScroll = this.onHorizontalScroll
    var style    = horizontalScrollbarStyle
    var minWidth = props.scrollWidth

    var scroller = <div xref="horizontalScroller" className="z-horizontal-scroller" style={{width: minWidth}} />

    if (IS_MAC){
        //needed for mac safari
        scrollbar = <div
          style={style}
          className="z-horizontal-scrollbar mac-fix"
        >
          <div
            onScroll={onScroll}
            className="ref-horizontalScrollbar z-horizontal-scrollbar-fix"
          >
              {scroller}
          </div>
        </div>
    } else {
        scrollbar = <div
          style={style}
          className="ref-horizontalScrollbar z-horizontal-scrollbar"
          onScroll={onScroll}
        >
          {scroller}
        </div>
    }

    return scrollbar
  }

  renderLoadMask(props) {
    if (props.loadMask){
      var loadMaskProps = assign({ visible: props.loading }, props.loadMaskProps)

      var defaultFactory = LoadMaskFactory
      var factory = typeof props.loadMask == 'function'?
              props.loadMask:
              defaultFactory

      var mask = factory(loadMaskProps)

      if (mask === undefined){
        //allow the specified factory to just modify props
        //and then leave the rendering to the defaultFactory
        mask = defaultFactory(loadMaskProps)
      }

      return mask
    }
  }

  ////////////////////////////////////////////////
  //
  // PREPARE PROPS METHODS
  //
  ////////////////////////////////////////////////
  prepareProps(thisProps) {
    const props = assign({}, thisProps)

    props.className = this.prepareClassName(props)
    props.style     = this.prepareStyle(props)

    return props
  }

  prepareStyle(props) {
    let style = assign({}, props.style)

    if (props.height != null){
      style.height = props.height
    }

    if (props.width != null){
      style.width = props.width
    }

    if (props.normalizeStyles){
      style = normalize(style)
    }

    return style
  }

  prepareClassName(props) {
    let className = props.className || ''

    if (Scroller.className){
      className += ' ' + Scroller.className
    }

    return className
  }
}

Scroller.className = 'z-scroller'
Scroller.displayName = DISPLAY_NAME

assign(Scroller.prototype, {
  onVerticalScroll: onScroll('vertical'),
  onHorizontalScroll: onScroll('horizontal'),

  verticalScrollAt  : scrollAt('vertical'),
  horizontalScrollAt: scrollAt('horizontal'),

  syncHorizontalScrollbar: syncHorizontalScrollbar,
  syncVerticalScrollbar  : syncVerticalScrollbar
})

Scroller.propTypes = {
  loadMask: PT.oneOfType([
    PT.bool,
    PT.func
  ]),

  loading : PT.bool,
  normalizeStyles: PT.bool,

  scrollTop : PT.number,
  scrollLeft: PT.number,

  scrollWidth : PT.number.isRequired,
  scrollHeight: PT.number.isRequired,

  height: PT.number,
  width : PT.number,

  minScrollStep          : PT.number,
  minHorizontalScrollStep: PT.number,
  minVerticalScrollStep  : PT.number,

  virtualRendering: PT.oneOf([true]),

  preventDefaultVertical: PT.bool,
  preventDefaultHorizontal: PT.bool
},

Scroller.defaultProps = {
  'data-display-name': DISPLAY_NAME,
  loadMask: true,

  virtualRendering: true, //FOR NOW, only true is supported
  scrollbarSize: 20,

  scrollTop : 0,
  scrollLeft: 0,

  minScrollStep: 10,

  minHorizontalScrollStep: IS_FIREFOX? 40: 1,

  //since FF goes back in browser history on scroll too soon
  //chrome and others also do this, but the normal preventDefault in syncScrollbar fn prevents this
  preventDefaultHorizontal: IS_FIREFOX
}

export default Scroller
