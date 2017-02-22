'use strict';

var getPrefix     = require('./getPrefix')
var forcePrefixed = require('./forcePrefixed')
var el            = require('./el')

var MEMORY = {}
var STYLE
var ELEMENT

module.exports = function(key, value, force){

    ELEMENT = ELEMENT || el()
    STYLE   = STYLE   ||  ELEMENT.style

    var k = key + ': ' + value

    if (MEMORY[k]){
        return MEMORY[k]
    }

    var prefix
    var prefixed
    var prefixedValue

    if (force || !(key in STYLE)){

        prefix = getPrefix('appearance')

        if (prefix){
            prefixed = forcePrefixed(key, value)

            prefixedValue = '-' + prefix.toLowerCase() + '-' + value

            if (prefixed in STYLE){
                ELEMENT.style[prefixed] = ''
                ELEMENT.style[prefixed] = prefixedValue

                if (ELEMENT.style[prefixed] !== ''){
                    value = prefixedValue
                }
            }
        }
    }

    MEMORY[k] = value

    return value
}