var path = require('path')
var webpack = require('webpack')
var HtmlWebpackPlugin = require('html-webpack-plugin')
var HtmlWebpackInlineSourcePlugin = require('html-webpack-inline-source-plugin')
var WebpackCleanPlugin = require('webpack-clean');

module.exports = {
  context: __dirname,
  entry: {
    index: './js/index.js'
  },
  output: {
    path: path.resolve('../'),
    filename: "[name].js",
  },
  //devtool: 'source-map', TODO: Source maps aren't useful inlined right now, figure this out
  plugins: [
    new HtmlWebpackPlugin({
      filename:'columnchart.html',
      template:'./html/index.html',
      inlineSource: '.(js|css)$',
    }),
    new HtmlWebpackInlineSourcePlugin(),
    new WebpackCleanPlugin([
      '../index.js',
    ])
  ],

  module: {
    rules: [
      {
        test: /\.jsx?$/,
        // chartbuilder and included modules need their jsx compiled, but most node-modules do not
        // TODO: We do not need all of D3. Come up with a more useful D3 bundle, or import only
        // what we need in Chartbuilder.
        exclude: /node_modules(?!([\\]+|\/)(react-tangle|chartbuilder))/,
        loader: 'babel-loader',
        query: {presets: ['env', 'react']}  // to transform JSX into JS
      },
      {
        test: /\.css$/,
        use: [{
          loader: 'style-loader'
        }, {
          loader: 'css-loader'
        }]
      },
      {
        // font handling
        test: /\.(woff)$/,
        loader: 'url-loader',
        options: {
          limit: 25000,
          mimetype: 'application/font-woff',
          name: '../fonts/[name].[ext]'
        },
      }
    ]
  },

  resolve: {
    modules: ['node_modules', 'chartbuilder'],
    extensions: ['.js', '.jsx']
  },
}
