import React from 'react'
import { shallow } from 'enzyme'
import OutputPane from './OutputPane'
import { jsonResponseMock } from './test-utils'
import {OutputIframe} from "./OutputIframe";


describe('OutputPane', () => {

  it('Renders', () => {
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

    const tree = shallow(
          <OutputPane id={100} revision={1} api={api}/>
    );

    expect(tree).toMatchSnapshot();
    expect(tree.find('TableView')).toHaveLength(1);
  });

  it('Renders when no module id', () => {
    const tree = shallow(
            <OutputPane id={undefined} revision={1} api={{}}/>
    );

    expect(tree.find('TableView')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

  it('Iframe when htmloutput set', () => {
    const tree = shallow(
          <OutputPane
            id={undefined}
            workflow={{id:777,public:true,read_only:false}}
            selectedWfModuleId={999}
            revision={1}
            htmlOutput={true}
            api={{}}/>
    );

    expect(tree.find('OutputIframe')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

});


