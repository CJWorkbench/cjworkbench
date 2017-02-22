module.exports = [
    {
        test   : /\.(js|jsx)$/,
        loader : 'babel-loader',
        exclude: /node_modules/
    },
    {
        test   : /\.styl$/,
        loader : 'style-loader!css-loader!autoprefixer-loader!stylus-loader',
        exclude: /node_modules/
    },
    {
        test   : /\.css$/,
        loader : 'style-loader!css-loader!autoprefixer-loader',
        exclude: /node_modules/
    },
    {
        test   : /\.png$/,
        loader : 'url-loader?mimetype=image/png',
        exclude: /node_modules/
    }
]