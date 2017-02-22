'use strict';

var DataGrid  = require('../DataGrid')
var React     = require('react/addons')
var TestUtils = React.addons.TestUtils

var TABLE_CLASS         = 'z-table'
var ROW_CLASS           = 'z-row'
var CELL_CLASS          = 'z-cell'
var CELLTEXT_CLASS      = 'z-content'
var COLUMN_HEADER_CLASS = 'z-column-header'

var testUtils = require('../utils')

var render        = testUtils.render
var findWithClass = testUtils.findWithClass
var tryWithClass  = testUtils.tryWithClass
var generateMockData = testUtils.generateMockData


describe('DataGrid Test Suite - Basic', function(){

	xit('renders basic grid', function(){

        var data = generateMockData({type : 'local', len : 1})

        var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName' },
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ]

		var table = render(
			DataGrid({
				idProperty:'id',
                dataSource:data,
                columns:columns
			})
		)

        // check whether one row is populated
        var rows = tryWithClass(table, ROW_CLASS)
        rows.length
            .should
            .equal(1)

        // console.log(rows[0].getDOMNode().innerHTML);

        // check the contents of the row
        var tableDom = findWithClass(table, TABLE_CLASS)
        var cellTexts = tryWithClass(rows[0], CELLTEXT_CLASS)

        cellTexts[0].getDOMNode()
            .textContent
            .should.equal('1')

	})

    it('check header rendered for each column',function() {

        var data = generateMockData({type : 'local', len : 1})

        var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName' },
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ];

        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns
            })
        );

        // check headers are rendered for each column
        var expectedHeaders = ['#','First name','Last name','City','Email']
        var headers = []

        tryWithClass(table, COLUMN_HEADER_CLASS)
            .map(function(header) {
                headers.push(header.getDOMNode().textContent)
            })

        headers.should.eql(expectedHeaders)
    })

})
