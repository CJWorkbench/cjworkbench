var path = require("path")
var webpack = require('webpack')
var BundleTracker = require('webpack-bundle-tracker')

module.exports = {
  context: __dirname,

  // Each page gets its own bundle
  entry: {
    app: './assets/js/app',
    login: './assets/js/login',
    workflows: './assets/js/workflows.page',
    workflow: './assets/js/workflow.page'
  },

  output: {
    path: path.resolve('./assets/bundles/'),
    filename: "[name]-[hash].js",
  },

  plugins: [
    new BundleTracker({filename: './webpack-stats.json'}),
  ],

  module: {
    rules: [
      {
        test: /\.jsx?$/,
        // chartbuilder and included modules need their jsx compiled, but most node-modules do not
        exclude: /node_modules(?!\/(react-tangle))/,
        loader: 'babel-loader',
        query: {presets: ['es2015', 'react']}  // to transform JSX into JS
      },
      {
        test: /\.css$/,
        loader: 'style-loader!css-loader'
      },
    ]
  },

  resolve: {
    modules: ['node_modules', 'chartbuilder'],
    extensions: ['.js', '.jsx']
  },
}
