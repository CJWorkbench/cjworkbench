import React from 'react'
import assign from 'object-assign'

const DEFAULT_CLASS_NAME = 'react-load-mask__loader'
const LOADBAR_CLASSNAME = `${DEFAULT_CLASS_NAME}-loadbar`

const notEmpty = s => !!s

export default class Loader extends React.Component {

  render() {
    const props = this.props

    const style = assign({}, props.style, {
      width: props.size,
      height: props.size
    })

    const className = [
      props.className,
      DEFAULT_CLASS_NAME,
      props.theme && `${DEFAULT_CLASS_NAME}--theme-${props.theme}`
    ].filter(notEmpty).join(' ')

    return <div {...props} style={style} className={className}>
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--1`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--2`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--3`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--4`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--5`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--6`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--7`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--8`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--9`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--10`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--11`} />
      <div className={`${LOADBAR_CLASSNAME} ${LOADBAR_CLASSNAME}--12`} />
    </div>
  }
}

Loader.defaultProps = {
  size: 40
}
