/* globals afterEach, beforeEach, describe, expect, it, jest */
import { act } from 'react-dom/test-utils'
import { renderWithI18n } from '../i18n/test-utils'
import { fireEvent, waitFor } from '@testing-library/react'
import Workflows from './index'

describe('Workflow list page', () => {
  const testOwnedWorkflows = [
    {
      id: 1,
      name: 'Cleaning',
      owner_name: 'Fred Frederson',
      public: true,
      last_update: '2010-10-18T00:30:00'
    },
    {
      id: 2,
      name: 'Charting',
      owner_name: 'Fred Frederson',
      public: false,
      last_update: '2010-10-18T00:20:00'
    },
    {
      id: 3,
      name: 'Analysis',
      owner_name: 'Fred Frederson',
      public: false,
      last_update: '2010-10-18T07:45:00'
    }
  ]

  const testSharedWorkflows = [
    {
      id: 7,
      name: 'Messy data cleanup',
      owner_name: 'John Johnson',
      public: false,
      last_update: '2010-10-18T00:30:00'
    },
    {
      id: 8,
      name: 'Document search',
      owner_name: 'Sally Sallerson',
      public: true,
      last_update: '2010-10-18T00:45:00'
    }
  ]

  const testExampleWorkflows = [
    {
      id: 10,
      name: 'Demo 1',
      owner_name: 'Workbench',
      public: false,
      last_update: '2010-10-18T00:30:00'
    }
  ]

  const api = {
    duplicateWorkflow: jest.fn(),
    deleteWorkflow: jest.fn(),
    updateAclEntry: jest.fn(),
    deleteAclEntry: jest.fn(),
    setWorkflowPublic: jest.fn()
  }

  afterEach(() => {
    Object.keys(api).forEach(k => api[k].mockReset())
  })

  let globalConfirm
  beforeEach(() => {
    globalConfirm = global.confirm
    global.confirm = jest.fn()
  })
  afterEach(() => {
    global.confirm = globalConfirm
  })

  const renderUi = props =>
    renderWithI18n(
      <Workflows
        api={api}
        user={{ id: 1, stripeCustomerId: null, display_name: 'Example User' }}
        {...props}
      />
    )

  it('renders My workflows correctly', () => {
    const { container } = renderUi({
      currentPath: '/workflows',
      workflows: testOwnedWorkflows
    })
    expect(container).toMatchSnapshot()

    expect(container.querySelectorAll('tbody>tr')).toHaveLength(3)
  })

  it('renders Shared correctly', () => {
    const { container } = renderUi({
      currentPath: '/workflows/shared-with-me',
      workflows: testSharedWorkflows
    })
    expect(container).toMatchSnapshot()

    expect(container.querySelectorAll('tbody>tr')).toHaveLength(2)
  })

  it('renders Examples correctly', () => {
    const { container } = renderUi({
      currentPath: '/workflows/examples',
      workflows: testExampleWorkflows
    })
    expect(container).toMatchSnapshot()

    expect(container.querySelectorAll('tbody>tr')).toHaveLength(1)
  })

  it('deletes a workflow', async () => {
    // Tests handleWorkflowChanging, handleWorkflowChanged
    // See WorkflowContextMenu.test.js for fine-grained delete unit tests
    const { container, getByText, queryAllByTitle } = renderUi({
      currentPath: '/workflows',
      workflows: testOwnedWorkflows
    })

    let resolvePromise
    const promise = new Promise(resolve => {
      resolvePromise = resolve
    })
    api.deleteWorkflow.mockReturnValue(promise)
    global.confirm.mockReturnValue(true) // pretend the user clicked OK

    fireEvent.click(queryAllByTitle('menu')[1]) // [0] opens the nav.main-nav menu
    act(() => {
      fireEvent.click(getByText('Delete'))
    })

    expect(api.deleteWorkflow).toHaveBeenCalledWith(3) // 3 shows up on top
    expect(container.querySelectorAll('tbody>tr')).toHaveLength(3)
    expect(container.querySelector('tr.changing')).not.toBe(null)

    resolvePromise(null)
    await waitFor(() =>
      expect(container.querySelectorAll('tbody>tr')).toHaveLength(2)
    )
  })

  it('duplicates a workflow', async () => {
    // Tests handleWorkflowDuplicating, handleWorkflowDuplicated
    // See WorkflowContextMenu.test.js for fine-grained duplicate unit tests
    const { container, getByText, queryAllByTitle } = renderUi({
      currentPath: '/workflows',
      workflows: testOwnedWorkflows
    })

    let resolvePromise
    const promise = new Promise(resolve => {
      resolvePromise = resolve
    })
    api.duplicateWorkflow.mockReturnValue(promise)

    fireEvent.click(queryAllByTitle('menu')[1]) // [0] opens the nav.main-nav menu
    act(() => {
      fireEvent.click(getByText('Duplicate'))
    })

    expect(api.duplicateWorkflow).toHaveBeenCalledWith(3) // 3 shows up on top
    expect(container.querySelectorAll('tbody>tr')).toHaveLength(3)
    expect(container.querySelector('tr.changing')).not.toBe(null)

    resolvePromise({
      id: 12,
      name: 'Copied!',
      owner_name: 'Fred Frederson',
      public: false,
      last_update: '2021-02-08T15:56.000Z'
    })
    await waitFor(() =>
      expect(container.querySelectorAll('tbody>tr')).toHaveLength(4)
    )
  })

  it('owned pane should have create workflow link when no workflows', () => {
    const { getByText } = renderUi({ currentPath: '/workflows', workflows: [] })
    getByText('Create your first workflow') // or crash
  })

  it('should have a placeholder in the Shared pane', () => {
    const { getByText } = renderUi({
      currentPath: '/workflows/shared-with-me',
      workflows: []
    })
    getByText(/Workflows shared with you as collaborator will appear here/)
  })

  it('should have a placeholder in the Examples pane', () => {
    const { getByText } = renderUi({
      currentPath: '/workflows/examples',
      workflows: []
    })
    getByText('Publish workflows as examples using Django admin')
  })

  it('should sort by updated_at', async () => {
    const { container, getByText } = renderUi({
      currentPath: '/workflows/examples',
      workflows: testOwnedWorkflows
    })
    expect(container.textContent).toMatch(/Analysis.*Cleaning.*Charting/)
    fireEvent.click(getByText(/Updated.*sort-descending.svg/))
    expect(container.textContent).toMatch(/Charting.*Cleaning.*Analysis/)
    fireEvent.click(getByText(/Updated.*sort-ascending.svg/))
    expect(container.textContent).toMatch(/Analysis.*Cleaning.*Charting/)
  })

  it('should sort by name', async () => {
    const { container, getByText } = renderUi({
      currentPath: '/workflows/examples',
      workflows: testOwnedWorkflows
    })
    expect(container.textContent).toMatch(/Analysis.*Cleaning.*Charting/)
    fireEvent.click(getByText('Title'))
    expect(container.textContent).toMatch(/Analysis.*Charting.*Cleaning/)
    fireEvent.click(getByText(/Title.*sort-ascending.svg/))
    expect(container.textContent).toMatch(/Cleaning.*Charting.*Analysis/)
    fireEvent.click(getByText(/Title.*sort-descending.svg/))
    expect(container.textContent).toMatch(/Analysis.*Charting.*Cleaning/)
  })

  it('should not allow delete of shared-with-me workflows', () => {
    const { container } = renderUi({
      currentPath: '/workflows/shared-with-me',
      workflows: testSharedWorkflows
    })
    expect(container.querySelector('tbody .dropdown')).toBe(null)
  })

  it('should not allow delete of example workflows', () => {
    const { container } = renderUi({
      currentPath: '/workflows/examples',
      workflows: testExampleWorkflows
    })
    expect(container.querySelector('tbody .dropdown')).toBe(null)
  })
})
