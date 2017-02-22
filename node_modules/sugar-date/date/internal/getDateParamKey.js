'use strict';

var getOwnKey = require('../../common/internal/getOwnKey');

function getDateParamKey(params, key) {
  return getOwnKey(params, key) ||
         getOwnKey(params, key + 's') ||
         (key === 'day' && getOwnKey(params, 'date'));
}

module.exports = getDateParamKey;