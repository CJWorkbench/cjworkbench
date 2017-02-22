'use strict';

var Range = require('./internal/Range'),
    mathAliases = require('../common/var/mathAliases'),
    rangeIsValid = require('./internal/rangeIsValid'),
    defineOnPrototype = require('../common/internal/defineOnPrototype'),
    getRangeMemberNumericValue = require('./internal/getRangeMemberNumericValue');

var abs = mathAliases.abs;

defineOnPrototype(Range, {

  'span': function() {
    var n = getRangeMemberNumericValue(this.end) - getRangeMemberNumericValue(this.start);
    return rangeIsValid(this) ? abs(n) + 1 : NaN;
  }

});

// This package does not export anything as it is
// simply defining "span" on Range.prototype.