/* globals expect, test */
import f from './selectLoggedInUserRole'

test('owner => owner', () => {
  expect(f({
    loggedInUser: { email: 'alice@example.org' },
    workflow: {
      public: false,
      secret_id: null,
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe('owner')
})

test('editor => editor', () => {
  expect(f({
    loggedInUser: { email: 'bob@example.org' },
    workflow: {
      public: false,
      secret_id: null,
      acl: [{ email: 'bob@example.org', role: 'editor' }],
      owner_email: 'alice@example.org'
    }
  })).toBe('editor')
})

test('viewer => viewer', () => {
  expect(f({
    loggedInUser: { email: 'bob@example.org' },
    workflow: {
      public: false,
      secret_id: null,
      acl: [{ email: 'bob@example.org', role: 'viewer' }],
      owner_email: 'alice@example.org'
    }
  })).toBe('viewer')
})

test('anonymous on anonymous workflow => owner', () => {
  expect(f({
    loggedInUser: null,
    workflow: {
      public: false,
      secret_id: null,
      acl: [],
      owner_email: null
    }
  })).toBe('owner')
})

test('anonymous on public workflow => viewer', () => {
  expect(f({
    loggedInUser: null,
    workflow: {
      public: true,
      secret_id: null,
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe('viewer')
})

test('anonymous on secret-link workflow => viewer', () => {
  expect(f({
    loggedInUser: null,
    workflow: {
      public: false,
      secret_id: 'wsecret',
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe('viewer')
})
