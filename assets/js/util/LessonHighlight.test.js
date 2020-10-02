/* global describe, expect, it */
import PropTypes from 'prop-types'
import { matchLessonHighlight, LessonHighlightsType } from './LessonHighlight'

const isValid = (obj) => {
  const globalConsole = global.console
  let ret = true
  global.console = {
    error: (s) => { ret = false }
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
  it('should allow Module', () => {
    const valid = { type: 'Module', id_name: 'Foo', index: 1 }
    expect(isValid([valid])).toBe(true)
    expect(isValid([{ type: 'Module', foo: 'bar', index: 1 }])).toBe(false)
  })

  it('should allow Step', () => {
    const valid = { type: 'Step', moduleIdName: 'Foo' }
    expect(isValid([valid])).toBe(true)
    expect(isValid([{ ...valid, index: 2 }])).toBe(true)
    expect(isValid([{ type: 'Step', foo: 'bar' }])).toBe(false)
  })

  it('should allow StepContextButton', () => {
    const valid = { type: 'StepContextButton', moduleIdName: 'Foo', button: 'notes' }
    expect(isValid([valid])).toBe(true)
    expect(isValid([{ type: 'StepContextButton', moduleIdName: 'Foo', button: 'x' }])).toBe(false)
    expect(isValid([{ type: 'StepContextButton', xoduleName: 'Foo', button: 'notes' }])).toBe(false)
  })

  it('should allow EditableNotes', () => {
    const valid = { type: 'EditableNotes' }
    expect(isValid([valid])).toBe(true)
  })

  it('should match using deepEqual on array elements', () => {
    const valid = [{ type: 'Module', id_name: 'Foo', index: 2 }, { type: 'EditableNotes' }]
    expect(matchLessonHighlight(valid, { type: 'Module', id_name: 'Foo', index: 2 })).toBe(true)
    expect(matchLessonHighlight(valid, { type: 'Module', id_name: 'Bar', index: 2 })).toBe(false)
    expect(matchLessonHighlight(valid, { type: 'EditableNotes' })).toBe(true)
    expect(matchLessonHighlight(valid, { type: 'XditableNotes' })).toBe(false)
  })

  it('should partial-match', () => {
    const lessonHighlight = [{ type: 'Module', id_name: 'Foo' }, { type: 'EditableNotes' }]
    expect(matchLessonHighlight(lessonHighlight, { type: 'Module', id_name: 'Foo', index: 2 })).toBe(true)
  })

  it('should allow `null` as a "wildcard"', () => {
    const lessonHighlight = [{ type: 'Module', id_name: 'Foo', index: 2 }, { type: 'EditableNotes' }]
    expect(matchLessonHighlight(lessonHighlight, { type: 'Module', id_name: null, index: 2 })).toBe(true)
  })
})
