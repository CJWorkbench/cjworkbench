import React from 'react'
import Code from './Code'
import MultiLineString from './MultiLineString'
import SingleLineString from './SingleLineString'

export default function String_ (props) {
  if (props.syntax) {
    return <Code {...props} />
  } else if (props.isMultiline) {
    return <MultiLineString {...props} />
  } else {
    return <SingleLineString {...props} />
  }
}
