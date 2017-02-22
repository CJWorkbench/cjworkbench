
module.exports = {
    entry: "./test.js",
    output: {
      path: __dirname,
      filename: "test-bundle.js"
    },
    externals: {
      'react':  'window.React'
    },
};
