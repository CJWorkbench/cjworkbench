/* globals afterEach, beforeEach, describe, expect, it, jest */
import React from 'react'
import { okResponseMock } from '../test-utils'
import { renderWithI18n } from '../i18n/test-utils'
import { fireEvent, waitForElementToBeRemoved } from '@testing-library/react'
import Workflows from './index'

describe('Workflow list page', () => {
  const testWorkflows = {
    owned: [
      {
        id: 1,
        name: 'Cleaning',
        owner_name: 'Fred Frederson',
        public: true,
        is_owner: true,
        last_update: '2010-10-18T00:30:00'
      },
      {
        id: 2,
        name: 'Charting',
        owner_name: 'Fred Frederson',
        public: false,
        is_owner: true,
        last_update: '2010-10-18T00:20:00'
      },
      {
        id: 3,
        name: 'Analysis',
        owner_name: 'Fred Frederson',
        public: false,
        is_owner: true,
        last_update: '2010-10-18T07:45:00'
      }
    ],
    shared: [
      {
        id: 7,
        name: 'Messy data cleanup',
        owner_name: 'John Johnson',
        public: false,
        is_owner: false,
        last_update: '2010-10-18T00:30:00'
      },
      {
        id: 8,
        name: 'Document search',
        owner_name: 'Sally Sallerson',
        public: true,
        is_owner: false,
        last_update: '2010-10-18T00:45:00'
      }
    ],
    templates: [
      {
        id: 10,
        name: 'Demo 1',
        owner_name: 'Workbench',
        public: false,
        is_owner: false,
        last_update: '2010-10-18T00:30:00'
      }
    ]
  }

  const api = {
    duplicateWorkflow: jest.fn(),
    deleteWorkflow: okResponseMock()
  }
  const renderUi = (props) => renderWithI18n(
    <Workflows
      api={api}
      user={{ id: 1 }}
      {...props}
    />
  )

  let globalConfirm
  beforeEach(() => {
    globalConfirm = global.confirm
    global.confirm = jest.fn()
  })
  afterEach(() => {
    global.confirm = globalConfirm
  })

  it('renders My workflows correctly', () => {
    const { container, getByText } = renderUi({ workflows: testWorkflows })
    fireEvent.click(getByText('My workflows'))
    expect(container).toMatchSnapshot()

    // owned tab should have 3 workflows
    expect(container.querySelectorAll('.tab-pane.active .workflow')).toHaveLength(3)
    // Make sure there is a context menu for each workflow
    expect(container.querySelectorAll('.tab-pane.active .workflow .dropdown')).toHaveLength(3)
    // Make sure there is a metadata line for each workflow in the list
    expect(container.querySelectorAll('.tab-pane.active .workflow .metadata')).toHaveLength(3)
  })

  it('renders Shared correctly', () => {
    const { container, getByText } = renderUi({ workflows: testWorkflows })
    fireEvent.click(getByText('Shared with me'))
    expect(container).toMatchSnapshot()

    expect(container.querySelectorAll('.tab-pane.active .workflow')).toHaveLength(2)
  })

  it('renders Recipes correctly', () => {
    const { container, getByText } = renderUi({ workflows: testWorkflows })
    fireEvent.click(getByText('Recipes'))
    expect(container).toMatchSnapshot()

    expect(container.querySelectorAll('.tab-pane.active .workflow')).toHaveLength(1)
  })

  it('deletes a workflow', async () => {
    const { container, getByText } = renderUi({ workflows: testWorkflows })
    global.confirm.mockReturnValue(true) // pretend the user clicked OK

    fireEvent.click(container.querySelector('.workflow .dropdown button'))
    fireEvent.click(getByText('Delete')) // and now "confirm" will happen
    await waitForElementToBeRemoved(getByText('Analysis')) // alphabetically-first was deleted
  })

  it('duplicates a workflow', async () => {
    // let 2 workflows load in user's shared tab, duplicate 1 and activeTab should get set
    // to owned list with +1 workflow
    const { container, getByText, findByText } = renderUi({
      workflows: testWorkflows,
      api: {
        ...api,
        duplicateWorkflow: jest.fn(() => Promise.resolve({
          id: 666,
          name: 'Copy of Visualization',
          owner_name: 'Paul Plagarizer',
          public: false
        }))
      }
    })

    fireEvent.click(getByText('Shared with me'))
    fireEvent.click(container.querySelector('.tab-pane.active .workflow .dropdown button'))
    fireEvent.click(getByText('Duplicate'))
    await findByText('Copy of Visualization')
  })

  it('owned pane should have create workflow link when no workflows', () => {
    const workflows = { ...testWorkflows, owned: [] }
    const { container, getByText } = renderUi({ workflows })

    // Owned list should have no workflows, instead a create workflow link
    fireEvent.click(getByText('My workflows'))
    expect(container.querySelectorAll('.tab-pane.active .workflow')).toHaveLength(0)
    expect(getByText('Create your first workflow')).toBeTruthy()
  })

  it('should have a placeholder in the Shared pane', () => {
    const { getByText } = renderUi({
      workflows: { ...testWorkflows, shared: [] }
    })
    fireEvent.click(getByText('Shared with me'))
    expect(getByText(/Workflows shared with you as collaborator will appear here/)).toBeTruthy()
  })

  it('should have a placeholder in the Recipes pane', () => {
    const { getByText } = renderUi({
      workflows: { ...testWorkflows, templates: [] }
    })
    fireEvent.click(getByText('Recipes'))
    expect(getByText('Publish new recipes via the Django admin')).toBeTruthy()
  })

  it('should sort properly by date and name', async () => {
    const { container, getByText } = renderUi({ workflows: testWorkflows })

    // sort by date ascending
    fireEvent.click(getByText('Sort'))
    fireEvent.click(getByText('Oldest modified'))
    expect(container.querySelector('.tab-pane.active').textContent).toMatch(/Charting.*Cleaning.*Analysis/)

    // sort by date descending
    fireEvent.click(getByText('Sort'))
    fireEvent.click(getByText('Last modified'))
    expect(container.querySelector('.tab-pane.active').textContent).toMatch(/Analysis.*Cleaning.*Charting/)

    // sort by name ascending
    fireEvent.click(getByText('Sort'))
    fireEvent.click(getByText('Alphabetical'))
    expect(container.querySelector('.tab-pane.active').textContent).toMatch(/Analysis.*Charting.*Cleaning/)

    // sort by name descending
    fireEvent.click(getByText('Sort'))
    fireEvent.click(getByText('Reverse alphabetical'))
    expect(container.querySelector('.tab-pane.active').textContent).toMatch(/Cleaning.*Charting.*Analysis/)
  })

  it('should delete owned workflows', () => {
    const { container, queryByText } = renderUi({ workflows: testWorkflows })
    fireEvent.click(container.querySelector('.tab-pane.active .dropdown button'))
    expect(queryByText('Delete')).toBeTruthy()
    // Close the menu. Otherwise, Popper will cause an error during unmount.
    // https://github.com/popperjs/react-popper/issues/350
    fireEvent.click(container.querySelector('.tab-pane.active .dropdown button'))
  })

  it('should not allow delete of shared-with-me workflows', () => {
    const { container, getByText, queryByText } = renderUi({ workflows: testWorkflows })
    fireEvent.click(getByText('Shared with me'))
    fireEvent.click(container.querySelector('.tab-pane.active .dropdown button'))
    expect(queryByText('Delete')).toBeNull()
    // Close the menu. Otherwise, Popper will cause an error during unmount.
    // https://github.com/popperjs/react-popper/issues/350
    fireEvent.click(container.querySelector('.tab-pane.active .dropdown button'))
  })

  it('should not allow delete of templates', () => {
    const { container, getByText, queryByText } = renderUi({ workflows: testWorkflows })
    fireEvent.click(getByText('Recipes'))
    fireEvent.click(container.querySelector('.tab-pane.active .dropdown button'))
    expect(queryByText('Delete')).toBeNull()
    // Close the menu. Otherwise, Popper will cause an error during unmount.
    // https://github.com/popperjs/react-popper/issues/350
    fireEvent.click(container.querySelector('.tab-pane.active .dropdown button'))
  })
})
