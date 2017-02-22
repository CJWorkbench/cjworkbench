'use strict';

var Range = require('./internal/Range'),
    rangeClamp = require('./internal/rangeClamp'),
    defineOnPrototype = require('../common/internal/defineOnPrototype');

defineOnPrototype(Range, {

  'clamp': function(el) {
    return rangeClamp(this, el);
  }

});

// This package does not export anything as it is
// simply defining "clamp" on Range.prototype.