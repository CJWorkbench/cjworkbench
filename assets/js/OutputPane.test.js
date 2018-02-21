import React from 'react'
import { mount } from 'enzyme'
import OutputPane from './OutputPane'
import { jsonResponseMock } from './utils'


describe('OutputPane', () => {

  it('Fetches and renders', (done) => {

    var testData = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: ["a", "b", "c"],
      rows: [
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
      ]
    };

    var api = {
      render: jsonResponseMock(testData),
    };

    const tree = mount(<OutputPane id={100} revision={1} api={api}/>)

    // wait for promise to resolve, then see what we get
    setImmediate(() => {
      // should call API for its data, with correct module id
      expect(api.render.mock.calls).toHaveLength(1);
      expect(api.render.mock.calls[0][0]).toBe(100);

      expect(tree.find('.outputpane-header')).toHaveLength(1);
      expect(tree.find('.outputpane-data')).toHaveLength(1);
      expect(tree).toMatchSnapshot();
      done();
    });
  });


  it('Renders when no module id', () => {
    const tree = mount(<OutputPane id={undefined} revision={1} api={{}}/>)

    expect(tree.find('.outputpane-header')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

  it('Iframe when htmloutput set', () => {
    const tree = mount(<OutputPane
      id={undefined}
      revision={1}
      htmlOutput={true}
      api={{}}/>)

    expect(tree.find('OutputIframe')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

});


