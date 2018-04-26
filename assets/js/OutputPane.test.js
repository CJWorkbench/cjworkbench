import React from 'react'
import { mount } from 'enzyme'
import OutputPane from './OutputPane'
import { jsonResponseMock } from './utils'
import {OutputIframe} from "./OutputIframe";
import TableView from "./TableView"


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

  it('Passes the right sortColumn and sortDirection props', () => {
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

    const NON_SORT_MODULE_ID = 28;
    const SORT_MODULE_ID = 135;

    // A barebones workflow for testing the sort stuff
    var workflow = {
      wf_modules: [
          {
            id: NON_SORT_MODULE_ID,
            module_version: {
              module: {
                id_name: 'loadurl'
              }
            }
          },
          {
            id: SORT_MODULE_ID,
            module_version: {
              module: {
                id_name: 'sort-from-table'
              }
            },
            parameter_vals: [
                {
                  // column
                  value: 'b',
                },
                {
                  // dtype
                  value: 1
                },
                {
                  //direction
                  value: 2 // Descending
                }
            ]
          },
      ]
    }

    // Try a mount with the sort module selected, should have sortColumn and sortDirection
    var tree = mount(
        <OutputPane
            revision={1}
            id={100}
            api={api}
            workflow={workflow}
            selectedWfModuleId={SORT_MODULE_ID}
        />
    );
    var tableView = tree.find(TableView);
    expect(tableView).toHaveLength(1);
    expect(tableView.prop('sortColumn')).toBe('b');
    expect(tableView.prop('sortDirection')).toBe('DESC');

    // Try a mount with a non-sort module selected, sortColumn and sortDirection should be undefined
    tree = mount(
        <OutputPane
            revision={1}
            id={100}
            api={api}
            workflow={workflow}
            selectedWfModuleId={NON_SORT_MODULE_ID}
        />
    );
    tableView = tree.find(TableView);
    expect(tableView).toHaveLength(1);
    expect(tableView.prop('sortColumn')).toBeUndefined();
    expect(tableView.prop('sortDirection')).toBeUndefined();
  });


  it('Renders when no module id', () => {
    const tree = mount(<OutputPane id={undefined} revision={1} api={{}}/>)

    expect(tree.find('.outputpane-header')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

  it('Iframe when htmloutput set', () => {
    const tree = mount(<OutputPane
      id={undefined}
      workflow={{id:777,public:true}}
      selectedWfModuleId={999}
      revision={1}
      htmlOutput={true}
      api={{}}/>)

    expect(tree.find('OutputIframe')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

});


