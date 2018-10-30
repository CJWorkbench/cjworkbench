ycmd server
===========

To use YouCompleteMe on Neovim.

Expects all your code is in `~/src`, and your cjworkbench code is in
`~/src/cjworkbench/cjworkbench`.

In `~/.config/nvim/init.vim`:

* use Plugged
* install plugin: `Plug 'Valloric/YouCompleteMe'
* run `~/.local/share/nvim/plugged/YouCompleteMe/install.py`
* `let g:ycm_server_python_interpreter = '~/src/cjworkbench/cjworkbench/docker/ycmd/wrap-ycmd.sh'`
