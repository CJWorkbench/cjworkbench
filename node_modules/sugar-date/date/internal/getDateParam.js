'use strict';

var getDateParamKey = require('./getDateParamKey'),
    coreUtilityAliases = require('../../common/var/coreUtilityAliases');

var getOwn = coreUtilityAliases.getOwn;

function getDateParam(params, key) {
  return getOwn(params, getDateParamKey(params, key));
}

module.exports = getDateParam;