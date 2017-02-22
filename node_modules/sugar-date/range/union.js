'use strict';

var Range = require('./internal/Range'),
    defineOnPrototype = require('../common/internal/defineOnPrototype');

defineOnPrototype(Range, {

  'union': function(range) {
    return new Range(
      this.start < range.start ? this.start : range.start,
      this.end   > range.end   ? this.end   : range.end
    );
  }

});

// This package does not export anything as it is
// simply defining "union" on Range.prototype.