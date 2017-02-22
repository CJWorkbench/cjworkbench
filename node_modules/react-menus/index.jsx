'use strict';

require('./index.styl')
import { render } from 'react-dom'
var React = require('react')
var Menu  = require('./src')

var items = []

var i = 0
var len = 10

for (; i< len; i++){
    items.push({
        label: 'item ' + (i + 1),
        // disabled: true,
        onClick: function(e, obj, index){
            console.log('clicked', index);
            // debugger
        },
        fn: function(){
            // debugger
        },
        items: [
            {
                label: i
            }
        ]
    })
}

var App = React.createClass({

    handleItemClick: function() {
        console.log('item click', arguments)
    },

    render: function() {

        <Menu cellStyle={{padding: 10 }} at={[100, 100]}>
            <Menu.Item onClick={this.handleItemClick}>
                <Menu.Item.Cell>first</Menu.Item.Cell>
                <Menu>
                    <Menu.Item onClick={this.handleItemClick}>
                        <Menu.Item.Cell>first</Menu.Item.Cell>
                    </Menu.Item>
                </Menu>
            </Menu.Item>

            <Menu.Separator />
            <Menu.Item onClick={this.handleItemClick} label={1}>
                <Menu>
                    <Menu.Item onClick={this.handleItemClick}>
                        <Menu.Item.Cell>one</Menu.Item.Cell>
                    </Menu.Item>
                    <Menu.Item onClick={this.handleItemClick}>
                        <Menu.Item.Cell>two</Menu.Item.Cell>

                        <Menu>
                            <Menu.Item onClick={this.handleItemClick}>
                                <Menu.Item.Cell>one</Menu.Item.Cell>
                            </Menu.Item>
                            <Menu.Item onClick={this.handleItemClick}>
                                <Menu.Item.Cell>two</Menu.Item.Cell>
                            </Menu.Item>
                            <Menu.Item onClick={this.handleItemClick}>
                                <Menu>
                                    <Menu.Item onClick={this.handleItemClick}>
                                        <Menu.Item.Cell>one</Menu.Item.Cell>
                                    </Menu.Item>
                                    <Menu.Item onClick={this.handleItemClick}>
                                        <Menu.Item.Cell>two</Menu.Item.Cell>
                                    </Menu.Item>
                                    <Menu.Item onClick={this.handleItemClick}>
                                        <Menu.Item.Cell>three</Menu.Item.Cell>
                                    </Menu.Item>
                                </Menu>
                                <Menu.Item.Cell>three</Menu.Item.Cell>
                            </Menu.Item>
                        </Menu>
                    </Menu.Item>
                    <Menu.Item onClick={this.handleItemClick}>
                        <Menu.Item.Cell>three</Menu.Item.Cell>

                        <Menu>
                            <Menu.Item onClick={this.handleItemClick}>
                                <Menu.Item.Cell>3. one</Menu.Item.Cell>
                            </Menu.Item>
                            <Menu.Item onClick={this.handleItemClick}>
                                <Menu.Item.Cell>3. two</Menu.Item.Cell>
                            </Menu.Item>
                            <Menu.Item onClick={this.handleItemClick}>
                                <Menu.Item.Cell>3. three</Menu.Item.Cell>
                            </Menu.Item>
                        </Menu>
                    </Menu.Item>
                </Menu>

                <Menu.Item.Cell>one</Menu.Item.Cell>
                <Menu.Item.Cell>icon</Menu.Item.Cell>
            </Menu.Item>

            <Menu.Item onClick={this.handleItemClick} label={2}>
                                        <Menu.Item.Cell>two</Menu.Item.Cell>
                <Menu.Item.Cell>icon</Menu.Item.Cell>
                <Menu>
                    <Menu.Item onClick={this.handleItemClick}>
                        <Menu.Item.Cell>first in submenu</Menu.Item.Cell>
                    </Menu.Item>
                </Menu>
            </Menu.Item>
            <Menu.Item label={3}>
                <Menu.Item.Cell>three </Menu.Item.Cell>
                <Menu>
                    <Menu.Item>
                        <Menu.Item.Cell>hello</Menu.Item.Cell>
                    </Menu.Item>
                </Menu>
            </Menu.Item>
        </Menu>

        var t = {
            xdefault: {
                style: {
                    color: 'blue'
                },
                overStyle: {
                    color: 'red'
                }
            }
        }
        return (
            <div>
                <Menu theme="xdefault" themes={t} onChildClick={this.handleChildClick} onClick={this.handleClick} xmaxHeight={300} items={items} at={[100, 100]}/>
            </div>

        )
    },

    handleChildClick: function() {
        console.log('child clicked!')
    },

    handleClick: function(itemProps) {
        console.log('clicked !!!', arguments)
    }
})

render(<App />, document.getElementById('content'))