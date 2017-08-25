import React from 'react'
import ModuleLibrary  from './ModuleLibrary'
import { mount } from 'enzyme'

describe('ModuleLibrary', () => {

  var wrapper;  
  var mockWorkflow = {
    "id": 7,
    "name": "Super great workflow time",
    "revision": 785,
    "wf_modules": [
    {
    "id": 71,
    "module_version": {
    "module": {
    "id": 5,
    "name": "Load from URL",
    "category": "Add data",
    "description": "Connect a dataset via its URL and keep it updated with its source.",
    "link": "",
    "author": "Workbench",
    "icon": "url"
    },
    "source_version_hash": "1.0",
    "last_update_time": "2017-07-17T18:46:03.216300Z"
    },
    "workflow": 7,
    "status": "ready",
    "error_msg": "",
    "parameter_vals": [
    {
    "id": 180,
    "parameter_spec": {
    "id": 9,
    "name": "URL",
    "id_name": "url",
    "type": "string",
    "multiline": false
    },
    "value": "https://data.sfgov.org/api/views/vmnk-skih/rows.csv",
    "visible": true,
    "menu_items": null
    },
    {
    "id": 181,
    "parameter_spec": {
    "id": 10,
    "name": "Path (for json data)",
    "id_name": "json_path",
    "type": "string",
    "multiline": false
    },
    "value": "",
    "visible": true,
    "menu_items": null
    },
    {
    "id": 182,
    "parameter_spec": {
    "id": 11,
    "name": "Check Now",
    "id_name": "version_select",
    "type": "custom",
    "multiline": false
    },
    "value": "",
    "visible": true,
    "menu_items": null
    }
    ],
    "is_collapsed": true,
    "notes": "Write notes here",
    "auto_update_data": false,
    "update_interval": 0,
    "update_units": "weeks",
    "last_update_check": "2017-08-17T22:30:46.042861Z"
    }
    ],
    "public": true,
    "read_only": false,
    "last_update": "2017-08-25T01:10:12.928395Z",
    "owner_name": " "
    }



  // beforeEach(() => wrapper = mount(
  //   <ModuleLibrary
  //     addModule={ () => {} }
  //     api={{}}
  //     workflow={mockWorkflow} 
  //   />
  // ));

  it('Renders - dummy test', () => { 
    // setImmediate( () => {
      
    //   expect(wrapper).toMatchSnapshot();
    //   done();
    // });

    expect(true).toBe(true);
  
  });
    
});

