'use strict';

var toUpperFirst = require('./toUpperFirst')
var getPrefix    = require('./getPrefix')
var properties   = require('./prefixProps')

/**
 * Returns the given key prefixed, if the property is found in the prefixProps map.
 *
 * Does not test if the property supports the given value unprefixed.
 * If you need this, use './getPrefixed' instead
 */
module.exports = function(key, value){

	if (!properties[key]){
		return key
	}

	var prefix = getPrefix(key)

	return prefix?
				prefix + toUpperFirst(key):
				key
}