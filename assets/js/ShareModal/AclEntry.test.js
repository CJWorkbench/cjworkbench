/* globals describe, expect, it, jest */
import AclEntry from './AclEntry'
import { mountWithI18n } from '../i18n/test-utils'

describe('AclEntry', () => {
  // We mount() because we're testing both Role and AclEntry together.
  const wrapper = (props = {}) =>
    mountWithI18n(
      <AclEntry
        isReadOnly={false}
        email='user@example.org'
        role='viewer'
        updateAclEntry={jest.fn()}
        deleteAclEntry={jest.fn()}
        {...props}
      />
    )

  it('should render the email and role', () => {
    const w = wrapper({ email: 'a@example.com', role: 'editor' })
    expect(w.find('.email').text()).toEqual('a@example.com')
    expect(
      w.find('button.dropdown-toggle Trans[id="js.ShareModal.Role.editor"]')
    ).toHaveLength(1)
  })

  it('should change editor to viewer', () => {
    const w = wrapper({ email: 'a@example.com', role: 'editor' })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button[name="role"][value="viewer"]').simulate('click')
    expect(w.prop('updateAclEntry')).toHaveBeenCalledWith(
      'a@example.com',
      'viewer'
    )
  })

  it('should change viewer to editor', () => {
    const w = wrapper({ email: 'a@example.com', role: 'viewer' })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button[name="role"][value="editor"]').simulate('click')
    expect(w.prop('updateAclEntry')).toHaveBeenCalledWith('a@example.com', 'editor')
  })

  it('should no-op when trying to change viewer to viewer', () => {
    const w = wrapper({ email: 'a@example.com', role: 'viewer' })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button[name="role"][value="viewer"]').simulate('click')
    expect(w.prop('updateAclEntry')).not.toHaveBeenCalled()
  })

  it('should no-op when trying to change editor to editor', () => {
    const w = wrapper({ email: 'a@example.com', role: 'editor' })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button[name="role"][value="editor"]').simulate('click')
    expect(w.prop('updateAclEntry')).not.toHaveBeenCalled()
  })

  it('should delete', () => {
    const w = wrapper({ email: 'a@example.com' })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button[name="delete"]').simulate('click')
    expect(w.prop('deleteAclEntry')).toHaveBeenCalledWith('a@example.com')
  })

  it('should render read-only', () => {
    const w = wrapper({ isReadOnly: true, role: 'editor' })
    expect(w.find('.role Trans[id="js.shareModal.Role.editor"]')).toHaveLength(
      0
    )
    expect(w.find('button')).toHaveLength(0)
  })
})
