/* globals expect, test */
import { renderWithI18n } from '../i18n/test-utils'
import WorkflowsSharedWithMeMain from './WorkflowsSharedWithMeMain'

test('render a public workflow', () => {
  const workflows = [
    {
      id: 1,
      name: 'Workflow 1',
      public: true,
      last_update: '2021-03-29T19:56:12.123Z',
      acl: []
    }
  ]
  const { container } = renderWithI18n(
    <WorkflowsSharedWithMeMain workflows={workflows} user={null} />
  )

  expect(container.querySelector('td.privacy').textContent).toEqual('public')
  expect(container.querySelector('td.title a').href).toEqual('http://localhost/workflows/1')
})

test('render a private workflow', () => {
  const workflows = [
    {
      id: 1,
      name: "Alice's Workflow",
      public: false,
      last_update: '2021-03-29T19:56:12.123Z',
      acl: [{ email: 'bob@example.com', role: 'editor' }]
    }
  ]
  const bob = { email: 'bob@example.com' }
  const { container } = renderWithI18n(
    <WorkflowsSharedWithMeMain workflows={workflows} user={bob} />
  )

  expect(container.querySelector('td.privacy').textContent).toEqual('private')
  expect(container.querySelector('td.title a').href).toEqual('http://localhost/workflows/1')
})

test('render a report-only private workflow', () => {
  const workflows = [
    {
      id: 1,
      name: "Alice's Workflow",
      public: false,
      last_update: '2021-03-29T19:56:12.123Z',
      acl: [{ email: 'bob@example.com', role: 'report-viewer' }]
    }
  ]
  const bob = { email: 'bob@example.com' }
  const { container } = renderWithI18n(
    <WorkflowsSharedWithMeMain workflows={workflows} user={bob} />
  )

  expect(container.querySelector('td.privacy').textContent).toEqual('private report')
  expect(container.querySelector('td.title a').href).toEqual('http://localhost/workflows/1/report')
})
