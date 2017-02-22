'use strict';

var PRIVATE_PROP_PREFIX = require('../var/PRIVATE_PROP_PREFIX'),
    coreUtilityAliases = require('../var/coreUtilityAliases');

var setProperty = coreUtilityAliases.setProperty;

function privatePropertyAccessor(key) {
  var privateKey = PRIVATE_PROP_PREFIX + key;
  return function(obj, val) {
    if (arguments.length > 1) {
      setProperty(obj, privateKey, val);
      return obj;
    }
    return obj[privateKey];
  };
}

module.exports = privatePropertyAccessor;