/* global describe, it, expect, jest */
import WorkbenchAceEditor from './AceEditor'
import { shallow } from 'enzyme'
import AceEditor from 'react-ace/lib/ace'

describe('AceEditor', () => {
  const defaultProps = {
    name: 'code',
    syntax: 'python',
    value: 'def process(table)\n    return table',
    onChange: jest.fn(),
    isZenMode: false
  }

  it('matches snapshot', () => {
    const wrapper = shallow(
      <WorkbenchAceEditor
        {...defaultProps}
        save={jest.fn()}
        stepOutputErrors={[]}
      />
    )
    expect(wrapper).toMatchSnapshot()
  })

  it('annotates an error', () => {
    const wrapper = shallow(
      <WorkbenchAceEditor
        {...defaultProps}
        save={jest.fn()}
        stepOutputErrors={[{ message: 'Line 1: Foo happened', quickFixes: [] }]}
      />
    )
    expect(wrapper.find(AceEditor).prop('annotations')).toEqual([
      { row: 0, type: 'error', text: 'Foo happened' }
    ])
  })
})
