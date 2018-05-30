import { Provider } from 'react-redux'
import React from 'react'
import { shallow } from 'enzyme'
import TestBackend from 'react-dnd-test-backend'
import {DragDropContext} from 'react-dnd'


// --- Mock API responses ---

export function mockResponse (status, statusText, response) {
  return new window.Response(response, {
    status: status,
    statusText: statusText,
    headers: {
      'Content-type': 'application/json'
    }
  });
};

// Returns new mock function that returns given json. Used for mocking "get" API calls
export function jsonResponseMock (json) {
  return jest.fn().mockImplementation(()=>
    Promise.resolve(json)
  )
}

// Returns new mock function that gives an OK HTTP response. Use for mocking "set" API calls
export function okResponseMock () {
  return jsonResponseMock(null)
}

export function wrapInTestContext(DecoratedComponent) {
  return DragDropContext(TestBackend)(
    React.createClass({
      render: function () {
        return <DecoratedComponent {...this.props} />;
      }
    })
  );
};


/**
 * Like enzyme's `shallow()`, but child components that depend on redux
 * don't crash the mount.
 *
 * See https://github.com/airbnb/enzyme/issues/472
 */
export function shallowWithStubbedStore(component) {
  const stub = () => ({})
  const store = { getState: stub, subscribe: stub, dispatch: stub }
  return shallow(<Provider store={store}>{component}</Provider>).dive()
}

// Guarantees for writing tests:
// - At least three modules
// - Module ids increment by 10
// - First module adds data and has data versions and unread notifications
export const genericTestWorkflow = {
  id: 999,
  selected_wf_module: 30,  // different than test_state.selected_wf_module so we can test setting state.selected_wf_module
  wf_modules: [
    {
      id: 10,
      parameter_vals: [
        {
          id: 1,
          parameter_spec : {
            id_name: 'data',
          },
          value: 'Some Data'
        }
      ],
      versions: {
        selected: "2018-02-21T03:09:20.214054Z",
        versions: [
          ["2018-02-21T03:09:20.214054Z", true],
          ["2018-02-21T03:09:15.214054Z", false],
          ["2018-02-21T03:09:10.214054Z", false]
        ]
      },
      notification_count: 2
    },
    {
      id: 20
    },
    {
      id: 30
    },
  ],
};


// Test module data
export const genericTestModules = [
  {
    "id":1,
    "name":"Chartbuilder",
    "category":"Visualize",
    "description":"Create line, column and scatter plot charts.",
    "icon":"chart"
  },
  {
    "id":2,
    "name":"Load from Facebork",
    "category":"Add data",
    "description":"Import from your favorite snowshall media",
    "icon":"url"
  },
  {
    "id":3,
    "name":"Load from Enigma",
    "category":"Add data",
    "description":"Connect a dataset from Enigma's collection via URL.",
    "icon":"url"
  },
  {
    "id":4,
    "name":"Other Module 1",
    "category":"other category",    // test modules outside the predefined categories
    "icon":"url"
  },
  {
    "id":5,
    "name":"Other Module 2",
    "category":"x category",
    "icon":"url"
  },
  {
    "id":6,
    "name":"Other Module 3",
    "category":"other category",
    "icon":"url"
  },
];