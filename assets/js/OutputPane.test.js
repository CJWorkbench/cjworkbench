import React from 'react'
import { mount } from 'enzyme'
import OutputPane from './OutputPane'
import { jsonResponseMock } from './test-utils'
import {OutputIframe} from "./OutputIframe";
import TableView from "./TableView"
import DataGrid from "./DataGrid"
import TestBackend from 'react-dnd-test-backend'
import { DragDropContextProvider } from 'react-dnd'


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

    const tree = mount(
        <DragDropContextProvider backend={TestBackend}>
          <OutputPane id={100} revision={1} api={api}/>
        </DragDropContextProvider>
    );

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
    const tree = mount(
        <DragDropContextProvider backend={TestBackend}>
            <OutputPane id={undefined} revision={1} api={{}}/>
        </DragDropContextProvider>
    );

    expect(tree.find('.outputpane-header')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

  it('Iframe when htmloutput set', () => {
    const tree = mount(
        <DragDropContextProvider backend={TestBackend}>
          <OutputPane
            id={undefined}
            workflow={{id:777,public:true}}
            selectedWfModuleId={999}
            revision={1}
            htmlOutput={true}
            api={{}}/>
        </DragDropContextProvider>
    );

    expect(tree.find('OutputIframe')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

});


