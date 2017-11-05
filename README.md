# corral
### A neovim plugin to keep you within your boundaries

Corral is a small plugin with a single purpose: to prevent me from accidentally
editing files outside of the repository I'm working in. If this is also a
problem you have, congratulations, you have found the solution!

## Functionality
When corral is enabled, it will observe your current working directory.
Whenever you are inside of a VCS repository (currently git and svn are 
supported, and only git is tested), any files that you open from outside of the 
repository's directory tree will automatically have their buffers marked
`readonly` and `nomodifiable`.  You will also get a message indicating that this 
has happened.

## Interface
Corral exposes the following commands:
- `:CorralEnable` to turn it on.
- `:CorralDisable` to turn it off.
- `:CorralToggle` to do whichever one of those isn't currently the case
    (for bindings).

Note that enabling corral does not affect existing buffers until they are
re-read. Disabling it currently never releases existing corralled buffers. You
can always do `:set noreadonly modifiable` yourself, however.

It also sets the variable `b:corralled` on each buffer that it corrals,
allowing this information to be used by other plugins.

## TODO
- Expose the settings dictionary as global variables, so you can use it.
- Test svn support.
- Add a `:CorralClean` command to delete all corralled buffers, making the
    workspace squeaky clean.
- Add `:CorralRelease` to 'free' all corralled buffers.
- Add an option to be 'proactive' and scan all existing buffers when enabling
    or disabling.

## FAQ
**Q:** I'm confused, does 'corralled' refer to the buffers inside or outside of
    the repository?

**A:** It's not a perfect metaphor, ok? (More seriously though, corral only
    concerns itself with the behavior of buffers outside of the repository.)

**Q:** Can it support *my favorite VCS*?

**A:** Yeah, probably. All that corral needs to support a given VCS is 
    a command in the `vcs_commands` dictionary that returns the root of a
    repository or exits non-zero if the command was not run within a
    repository. If you have such a command, feel free to submit a PR and I'll
    probably merge it!
