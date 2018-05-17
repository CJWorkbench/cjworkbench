import PropTypes from 'prop-types'
import { matchLessonHighlight, LessonHighlightsType } from './LessonHighlight'

const isValid = (obj) => {
  const globalConsole = global.console
  let ret = true
  global.console = {
    error: function(s) { ret = false }
  }

  const displayName = 'LessonHighlight' + Math.floor(99999999 * Math.random()) // random name => React never hides logs
  PropTypes.checkPropTypes(
    { elements: LessonHighlightsType.isRequired },
    { elements: obj },
    'element',
    displayName
  )
  // if checkPropTypes outputs error, our global.console hack will
  // eat the error message and set ret=false.

  global.console = globalConsole
  return ret
}

describe('LessonHighlight', () => {
  it('should allow MlModule', () => {
    const valid = { type: 'MlModule', name: 'Foo' }
    expect(isValid([ valid ])).toBe(true)
    expect(isValid([ { type: 'MlModule', foo: 'bar' } ])).toBe(false)
  })

  it('should allow WfModule', () => {
    const valid = { type: 'WfModule', moduleName: 'Foo' }
    expect(isValid([ valid ])).toBe(true)
    expect(isValid([ { type: 'WfModule', foo: 'bar' } ])).toBe(false)
  })

  it('should allow WfModuleContextButton', () => {
    const valid = { type: 'WfModuleContextButton', moduleName: 'Foo', button: 'notes' }
    expect(isValid([ valid ])).toBe(true)
    expect(isValid([ { type: 'WfModuleContextButton', moduleName: 'Foo', button: 'x' } ])).toBe(false)
    expect(isValid([ { type: 'WfModuleContextButton', xoduleName: 'Foo', button: 'notes' } ])).toBe(false)
  })

  it('should allow EditableNotes', () => {
    const valid = { type: 'EditableNotes' }
    expect(isValid([ valid ])).toBe(true)
  })

  it('should allow ModuleSearch', () => {
    const valid = { type: 'ModuleSearch' }
    expect(isValid([ valid ])).toBe(true)
  })

  it('should match using deepEqual on array elements', () => {
    const valid = [ { type: 'MlModule', name: 'Foo' }, { type: 'EditableNotes' } ]
    expect(matchLessonHighlight(valid, { type: 'MlModule', name: 'Foo' })).toBe(true)
    expect(matchLessonHighlight(valid, { type: 'MlModule', name: 'Bar' })).toBe(false)
    expect(matchLessonHighlight(valid, { type: 'EditableNotes' })).toBe(true)
    expect(matchLessonHighlight(valid, { type: 'XditableNotes' })).toBe(false)
  })
})
