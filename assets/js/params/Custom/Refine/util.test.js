/* globals describe, expect, it */
import { massRename } from './util'

describe('util', () => {
  // Most of this is untested because it's copy/pasted from our Python code
  // (which has unit tests). So the only possible errors are transcription
  // errors.
  describe('massRename', () => {
    it('should work in the simplest case', () => {
      expect(massRename({}, { foo: 'bar' })).toEqual({ foo: 'bar' })
    })

    it('should rename an existing rename', () => {
      expect(massRename({ a: 'b' }, { b: 'c' })).toEqual({ a: 'c', b: 'c' })
    })

    it('should rename a group that does not have its fromGroup as a member', () => {
      expect(massRename(
        // Two groups: 'b' (contains original 'a') and 'c' (contains original 'b' and 'c')
        { a: 'b', b: 'c' },
        // Rename group 'b'
        { b: 'd' }
      )).toEqual({ a: 'd', b: 'c' })
      // New groups: 'd' (contains original 'a') and 'c' (contains original 'b' and 'c')
    })

    it('should rename a group that does have its fromGroup as a member', () => {
      expect(massRename(
        // Two groups: 'b' (contains original 'a') and 'c' (contains original 'b' and 'c')
        { a: 'b', b: 'c' },
        // Rename group 'c'
        { c: 'd' }
      )).toEqual({ a: 'b', b: 'd', c: 'd' })
      // New groups: 'b' (contains original 'a') and 'd' (contains original 'b' and 'c')
    })

    it('should swap two groups', () => {
      expect(massRename(
        { a: 'x', b: 'x', c: 'y', d: 'y' },
        { x: 'y', y: 'x' }
      )).toEqual({ a: 'y', b: 'y', x: 'y', c: 'x', d: 'x', y: 'x' })
    })
  })
})
