/* globals describe, expect, it, jest */
import { shallow } from 'enzyme'
import EditableWorkflowName from './EditableWorkflowName'

describe('EditableWorkflowName', () => {
  const wrapper = (extraProps = {}) => {
    return shallow(
      <EditableWorkflowName
        value='A'
        onSubmit={jest.fn()}
        isReadOnly={false}
        {...extraProps}
      />
    )
  }

  it('renders a plain title when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('input')).toHaveLength(0)
  })

  it('lets the user edit the title', () => {
    const onSubmit = jest.fn()
    const w = wrapper({ onSubmit })
    w.find('input').simulate('change', { target: { value: 'B' } })
    w.find('input').simulate('blur')
    expect(onSubmit).toHaveBeenCalledWith('B')
  })
})
