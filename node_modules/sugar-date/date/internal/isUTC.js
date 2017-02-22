'use strict';

var _utc = require('../../common/var/_utc'),
    tzOffset = require('./tzOffset');

function isUTC(d) {
  return !!_utc(d) || tzOffset(d) === 0;
}

module.exports = isUTC;