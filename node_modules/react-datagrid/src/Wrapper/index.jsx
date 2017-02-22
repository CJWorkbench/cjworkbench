'use strict';

var React    = require('react')
var assign   = require('object-assign')
var Scroller = require('react-virtual-scroller')

function emptyFn(){}

module.exports = React.createClass({

    displayName: 'ReactDataGrid.Wrapper',

    propTypes: {
        scrollLeft   : React.PropTypes.number,
        scrollTop    : React.PropTypes.number,
        scrollbarSize: React.PropTypes.number,
        rowHeight   : React.PropTypes.any,
        renderCount : React.PropTypes.number
    },

    getDefaultProps: function(){
        return {
            scrollLeft: 0,
            scrollTop : 0
        }
    },

    onMount: function(scroller){
        ;(this.props.onMount || emptyFn)(this, scroller)
    },

    render: function() {

        var props     = this.prepareProps(this.props)
        var rowsCount = props.renderCount

        var groupsCount = 0
        if (props.groupData){
            groupsCount = props.groupData.groupsCount
        }

        rowsCount += groupsCount

        // var loadersSize = props.loadersSize
        var verticalScrollerSize = (props.totalLength + groupsCount) * props.rowHeight// + loadersSize

        var content = props.empty?
            <div className="z-empty-text" style={props.emptyTextStyle}>{props.emptyText}</div>:
            <div {...props.tableProps} ref="table"/>


        return <Scroller
                onMount={this.onMount}
                preventDefaultHorizontal={true}

                loadMask={!props.loadMaskOverHeader}
                loading={props.loading}

                scrollbarSize={props.scrollbarSize}

                minVerticalScrollStep={props.rowHeight}
                scrollTop={props.scrollTop}
                scrollLeft={props.scrollLeft}

                scrollHeight={verticalScrollerSize}
                scrollWidth={props.minRowWidth}

                onVerticalScroll={this.onVerticalScroll}
                onHorizontalScroll={this.onHorizontalScroll}
            >
            {content}
        </Scroller>
    },

    onVerticalScrollOverflow: function() {
    },

    onHorizontalScrollOverflow: function() {
    },

    onHorizontalScroll: function(scrollLeft) {
        this.props.onScrollLeft(scrollLeft)
    },

    onVerticalScroll: function(pos){
        this.props.onScrollTop(pos)
    },

    prepareProps: function(thisProps){
        var props = {}

        assign(props, thisProps)

        return props
    }
})
