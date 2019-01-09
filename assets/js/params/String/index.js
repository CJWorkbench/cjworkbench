import React from 'react'
import MultiLineString from './MultiLineString'
import SingleLineString from './SingleLineString'

export default function String_ (props) {
  const Component = props.isMultiline ? MultiLineString : SingleLineString
  return <Component {...props} />
}
