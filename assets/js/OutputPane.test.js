import React from 'react'
import { mount } from 'enzyme'
import fetchMock from 'jest-fetch-mock'
import OutputPane from './OutputPane'

it('Fetches and renders', (done) => {

  var testData =
    [
      {
      "a": "1",
      "b": "2",
      "c": "3"
      },
      {
      "a": "4",
      "b": "5",
      "c": "6"
      }
    ];

  fetch.mockResponse(JSON.stringify(testData));

  const tree = mount( <OutputPane id={1} revision={1}/> )

  // wait for everything to update, then see what we get
  setImmediate( () => {
    expect(tree).toMatchSnapshot();
    done();
  });
});


it('No output when no module id', () => {
  const tree = mount( <OutputPane id={undefined} revision={1}/> )
  tree.update();
  expect(tree).toMatchSnapshot();
});


