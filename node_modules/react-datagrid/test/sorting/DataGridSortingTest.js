'use strict';

var DataGrid  = require('../DataGrid')
var React     = require('react/addons')
var TestUtils = React.addons.TestUtils

var TABLE_CLASS         = 'z-table'
var ROW_CLASS           = 'z-row'
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

var columns = [
    { name: 'index', title: '#', width: 50 },
    { name: 'firstName'},
    { name: 'lastName'  },
    { name: 'city' },
    { name: 'email' }
];

describe('DataGrid Test Suite -  Sorting',function() {

    it('Check presence of sort indicator (single sorting), given the sort info object',function() {
        
        var data = generateMockData({type : 'local',len : 1})
        var SORT_INFO = [ { name: 'firstName', dir: 'asc'}]

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns,
                sortInfo : SORT_INFO
            })
        )

        var headers = tryWithClass(table,COLUMN_HEADER_CLASS)
        var checkHeader = React.findDOMNode(headers[1])
        checkHeader.className.includes(SORT_ASC_CLASS).should.be.true

    })

    it('Check presence of sort indicator (multiple sorting), given the sort info object',function() {
        
        var data = generateMockData({type : 'local',len : 1})
        var SORT_INFO = [ { name: 'firstName', dir: 'asc'} , { name : 'lastName', dir : 'asc'}]

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns,
                sortInfo : SORT_INFO
            })
        )

        var headers = tryWithClass(table,COLUMN_HEADER_CLASS)
        var checkHeader1 = React.findDOMNode(headers[1])
        var checkHeader2 = React.findDOMNode(headers[2])
        checkHeader1.className.includes(SORT_ASC_CLASS).should.be.true
        checkHeader2.className.includes(SORT_ASC_CLASS).should.be.true

    })

    it('Check onSortChange calling',function() {

        var data = generateMockData({type : 'local',len : 1})
        var SORT_INFO = [ { name: 'firstName', dir: 'asc'}]
        var checkDir = -1

        var onSortChangeHandler = function(sortInfo) {
            sortInfo.length.should.equal(1)
            sortInfo[0].name.should.equal('firstName')
            sortInfo[0].dir.should.equal(checkDir)    
        }

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns,
                sortInfo : SORT_INFO,
                onSortChange : onSortChangeHandler
            })
        )

        var headers = tryWithClass(table,COLUMN_HEADER_CLASS)
        var checkHeader = React.findDOMNode(headers[1])
        checkHeader.className.includes(SORT_ASC_CLASS).should.be.true

        TestUtils.Simulate.mouseDown(checkHeader)
        TestUtils.Simulate.mouseUp(checkHeader)

    })

    it('Check onSortChange calling (multiple sortInfo)',function() {

        var data = generateMockData({type : 'local',len : 1})
        var SORT_INFO = [ { name: 'firstName', dir: 'asc'}, { name : 'lastName', dir : 'asc'}]
        var checkDir = -1
        var originalDir = 'asc'

        var onSortChangeHandler = function(sortInfo) {
            sortInfo.length.should.equal(2)
            sortInfo[0].name.should.equal('firstName')
            sortInfo[0].dir.should.equal(checkDir)
            sortInfo[1].name.should.equal('lastName')
            sortInfo[1].dir.should.equal(originalDir)    
        }

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns,
                sortInfo : SORT_INFO,
                onSortChange : onSortChangeHandler
            })
        )

        var headers = tryWithClass(table,COLUMN_HEADER_CLASS)
        var checkHeader = React.findDOMNode(headers[1])
        checkHeader.className.includes(SORT_ASC_CLASS).should.be.true

        TestUtils.Simulate.mouseDown(checkHeader)
        TestUtils.Simulate.mouseUp(checkHeader)

    })

    

})