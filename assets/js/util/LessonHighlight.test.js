import { validLessonHighlight, matchLessonHighlight, stateHasLessonHighlight } from './LessonHighlight'

const globalConsole = global.console

describe('LessonHighlight', () => {
  beforeEach(() => {
    global.console = {
      error: function(s) { throw new Error(s) }
    }
  })

  afterEach(() => {
    global.console = globalConsole
  })

  it('should allow MlModule', () => {
    const valid = { type: 'MlModule', name: 'Foo' }
    expect(validLessonHighlight([ valid ])).toEqual([ valid ])
    expect(() => validLessonHighlight([ { type: 'MlModule', foo: 'bar' } ])).toThrow()
  })

  it('should turn Object param into Array', () => {
    const valid = { type: 'MlModule', name: 'Foo' }
    expect(validLessonHighlight(valid)).toEqual([ valid ])
  })

  it('should allow WfModule', () => {
    const valid = { type: 'WfModule', name: 'Foo' }
    expect(validLessonHighlight([ valid ])).toEqual([ valid ])
    expect(() => validLessonHighlight([ { type: 'WfModule', foo: 'bar' } ])).toThrow()
  })

  it('should allow WfParameter', () => {
    const valid = { type: 'WfParameter', moduleName: 'Foo', name: 'bar' }
    expect(validLessonHighlight([ valid ])).toEqual([ valid ])
    expect(() => validLessonHighlight([ { type: 'WfParameter', name: 'bar' } ])).toThrow()
    expect(() => validLessonHighlight([ { type: 'WfParameter', moduleName: 'Foo' } ])).toThrow()
  })

  it('should allow WfModuleContextButton', () => {
    const valid = { type: 'WfModuleContextButton', moduleName: 'Foo', button: 'notes' }
    expect(validLessonHighlight([ valid ])).toEqual([ valid ])
    expect(() => validLessonHighlight([ { type: 'WfModuleContextButton', moduleName: 'Foo', button: 'x' } ])).toThrow()
    expect(() => validLessonHighlight([ { type: 'WfModuleContextButton', xoduleName: 'Foo', button: 'notes' } ])).toThrow()
  })

  it('should allow EditableNotes', () => {
    const valid = { type: 'EditableNotes' }
    expect(validLessonHighlight([ valid ])).toEqual([ valid ])
  })

  it('should allow ModuleSearch', () => {
    const valid = { type: 'ModuleSearch' }
    expect(validLessonHighlight([ valid ])).toEqual([ valid ])
  })

  it('should match using deepEqual on array elements', () => {
    const valid = [ { type: 'MlModule', name: 'Foo' }, { type: 'EditableNotes' } ]
    expect(matchLessonHighlight(valid, { type: 'MlModule', name: 'Foo' })).toBe(true)
    expect(matchLessonHighlight(valid, { type: 'MlModule', name: 'Bar' })).toBe(false)
    expect(matchLessonHighlight(valid, { type: 'EditableNotes' })).toBe(true)
    expect(matchLessonHighlight(valid, { type: 'XditableNotes' })).toBe(false)
  })

  it('should have stateHasLessonHighlight', () => {
    const f = stateHasLessonHighlight({ type: 'MlModule', name: 'Foo' })
    expect(f({ lesson_highlight: [ { type: 'MlModule', name: 'Foo' }, { type: 'EditableNotes' } ] })).toBe(true)
    expect(f({ lesson_highlight: [] })).toBe(false)
    expect(f({ lesson_highlight: [ { type: 'EditableNotes' } ] })).toBe(false)
  })

  it('should make stateHasLessonHighlight throw an error on bad call', () => {
    expect(() => stateHasLessonHighlight({ type: 'NonValidType', name: 'Boo' })).toThrow()
  })

  it('should allow state.lesson_highlight=undefined (useful in unrelated unit tests)', () => {
    const f = stateHasLessonHighlight({ type: 'MlModule', name: 'Foo' })
    expect(f({})).toBe(false)
  })
})
