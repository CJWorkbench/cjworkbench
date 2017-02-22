'use strict';

var _utc = require('../../common/var/_utc'),
    trunc = require('../../common/var/trunc'),
    tzOffset = require('./tzOffset'),
    padNumber = require('../../common/internal/padNumber'),
    mathAliases = require('../../common/var/mathAliases');

var abs = mathAliases.abs;

function getUTCOffset(d, iso) {
  var offset = _utc(d) ? 0 : tzOffset(d), hours, mins, colon;
  colon  = iso === true ? ':' : '';
  if (!offset && iso) return 'Z';
  hours = padNumber(trunc(-offset / 60), 2, true);
  mins = padNumber(abs(offset % 60), 2);
  return  hours + colon + mins;
}

module.exports = getUTCOffset;