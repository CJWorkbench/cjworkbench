'use strict';

var coreUtilityAliases = require('../var/coreUtilityAliases');

var hasOwn = coreUtilityAliases.hasOwn;

function getOwnKey(obj, key) {
  if (hasOwn(obj, key)) {
    return key;
  }
}

module.exports = getOwnKey;