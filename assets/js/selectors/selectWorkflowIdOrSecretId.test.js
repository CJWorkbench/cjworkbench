/* globals expect, test */
import f from './selectWorkflowIdOrSecretId'

test('owner => id', () => {
  expect(f({
    loggedInUser: { email: 'alice@example.org' },
    workflow: {
      id: 123,
      public: false,
      secret_id: 'wsecret',
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe(123)
})

test('editor => id', () => {
  expect(f({
    loggedInUser: { email: 'bob@example.org' },
    workflow: {
      id: 123,
      public: false,
      secret_id: 'wsecret',
      acl: [{ email: 'bob@example.org', role: 'editor' }],
      owner_email: 'alice@example.org'
    }
  })).toBe(123)
})

test('viewer => id', () => {
  expect(f({
    loggedInUser: { email: 'bob@example.org' },
    workflow: {
      id: 123,
      public: false,
      secret_id: 'wsecret',
      acl: [{ email: 'bob@example.org', role: 'viewer' }],
      owner_email: 'alice@example.org'
    }
  })).toBe(123)
})

test('anonymous on lesson => id', () => {
  expect(f({
    loggedInUser: null,
    workflow: {
      id: 123,
      public: false,
      secret_id: null,
      acl: [],
      owner_email: null
    }
  })).toBe(123)
})

test('anonymous on public workflow => id', () => {
  expect(f({
    loggedInUser: null,
    workflow: {
      id: 123,
      public: true,
      secret_id: 'wsecret',
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe(123)
})

test('anonymous on secret-link workflow => secret', () => {
  expect(f({
    loggedInUser: null,
    workflow: {
      id: 123,
      public: false,
      secret_id: 'wsecret',
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe('wsecret')
})

test('user on lesson => id', () => {
  expect(f({
    loggedInUser: { email: 'bob@example.com' },
    workflow: {
      id: 123,
      public: false,
      secret_id: null,
      acl: [],
      owner_email: null
    }
  })).toBe(123)
})

test('user on public workflow => id', () => {
  expect(f({
    loggedInUser: { email: 'bob@example.com' },
    workflow: {
      id: 123,
      public: true,
      secret_id: 'wsecret',
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe(123)
})

test('user on secret-link workflow => secret', () => {
  expect(f({
    loggedInUser: { email: 'bob@example.com' },
    workflow: {
      id: 123,
      public: false,
      secret_id: 'wsecret',
      acl: [],
      owner_email: 'alice@example.org'
    }
  })).toBe('wsecret')
})
