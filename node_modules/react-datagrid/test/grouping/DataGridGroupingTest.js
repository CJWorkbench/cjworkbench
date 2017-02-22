'use strict';

var DataGrid  = require('../DataGrid')
var React     = require('react/addons')
var TestUtils = React.addons.TestUtils

var TABLE_CLASS         = 'z-table'
var ROW_CLASS           = 'z-row'
var GROUP_ROW_CLASS		= 'z-group-row'
var GROUPED_ROW_CLASS	= 'z-grouped'
var CELL_CLASS          = 'z-cell'
var CELL_TEXT_CLASS     = 'z-text'
var ALIGN_RIGHT_CLASS   = 'z-align-right'
var SORT_ASC_CLASS      = 'z-asc'
var SORT_DESC_CLASS     = 'z-desc'
var COLUMN_HEADER_CLASS = 'z-column-header'

var testUtils = require('../utils')

var render        = testUtils.render
var findWithClass = testUtils.findWithClass
var tryWithClass  = testUtils.tryWithClass
var generateMockData = testUtils.generateMockData


describe('DataGrid Test Suite -  Grouping',function() {

	xit('check groupBy prop works',function() {

		var data = generateMockData({type : 'local',len : 10})
		// prepare data for grouping
		data.map(function(row,index) {
			if(index%2) {
				row.country = 'USA'
			} else {
				row.country = 'India'
			}
		})

		var columns = [
		    { name: 'index', title: '#', width: 50 },
		    { name: 'firstName'},
		    { name: 'lastName'  },
		    { name: 'city' },
		    { name: 'email' },
		    { name: 'country'}
		];

		var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns,
                style	  : { height : 400 },
                groupBy	  : ['country']
            })
        )

        var groupHeaders = tryWithClass(table,GROUP_ROW_CLASS)
        groupHeaders.length.should.equal(2)
        React.findDOMNode(groupHeaders[0]).textContent.should.equal('India')
        React.findDOMNode(groupHeaders[1]).textContent.should.equal('USA') 

        var groupedRows = tryWithClass(table,GROUPED_ROW_CLASS)
        groupedRows.length.should.equal(10)
        groupedRows.map(function(row,index) {
        	var cells = tryWithClass(row,CELL_CLASS)
        	if(index < 5) {
        		React.findDOMNode(cells[5]).textContent.should.equal('India')
        	} else {
        		React.findDOMNode(cells[5]).textContent.should.equal('USA')
        	}
        })

	})
})
