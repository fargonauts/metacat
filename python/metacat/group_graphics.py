"""group-graphics.ss: drawing groups in the Workspace window (the engine's part).

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Metacat is based on Copycat, which was originally written in Common Lisp
by Melanie Mitchell.  Translated to Python (2026) from group-graphics.ss, with
racket/engine/group-graphics.rktl as a worked translation.

Only group-graphics is translated here, because the model calls it (workspace.py,
when %workspace-graphics% is on).  The rest of group-graphics.ss (the
%...-arrowhead...% constants, group-dashed-line-density, make-group-pexp and the
pexp builders) is translated in the panels item; make-group-pexp is read
through the package at call time (_metacat.group_graphics.make_group_pexp), so
it must be defined in this module by then.  group-graphics only sends messages
to *workspace-window* (setup.g_workspace_window) and the group; it draws
nothing itself, never draws a random number and never imports tkinter.
"""
from __future__ import annotations

import metacat as _metacat
from metacat import setup
from metacat.objects import tell
from metacat.utilities import exists_p


def group_graphics(op, group):
    """group-graphics.ss: group-graphics"""
    proposal_level = tell(group, "get-proposal-level")
    tell(setup.g_workspace_window, "caching-on")
    if op == "flash":
        if tell(group, "drawn?") is not False:
            tell(setup.g_workspace_window, "flash", tell(group, "get-graphics-pexp"))
        else:
            drawn_group = tell(group, "get-drawn-coincident-group")
            if (exists_p(drawn_group)
                    and proposal_level == tell(drawn_group, "get-proposal-level")):
                tell(setup.g_workspace_window, "flash", tell(drawn_group, "get-graphics-pexp"))
    elif op == "set-pexp-and-draw":
        tell(group, "set-graphics-pexp",
             _metacat.group_graphics.make_group_pexp(group, proposal_level))
        drawn_group = tell(group, "get-drawn-coincident-group")
        if not exists_p(drawn_group):
            tell(setup.g_workspace_window, "draw-group", group)
    elif op == "erase":
        if tell(group, "drawn?") is not False:
            tell(setup.g_workspace_window, "erase-group", group)
            # Repair damage to any overlapping groups:
            for g in tell(group, "get-drawn-overlapping-groups"):
                tell(setup.g_workspace_window, "draw-group", g)
            pending_group = tell(group, "get-highest-level-coincident-group")
            if exists_p(pending_group):
                tell(setup.g_workspace_window, "draw-group", pending_group)
    elif op == "update-level":
        new_pexp = _metacat.group_graphics.make_group_pexp(group, proposal_level)
        if tell(group, "drawn?") is not False:
            tell(setup.g_workspace_window, "erase", tell(group, "get-graphics-pexp"))
            tell(group, "set-graphics-pexp", new_pexp)
            tell(setup.g_workspace_window, "draw-group", group)
        else:
            tell(group, "set-graphics-pexp", new_pexp)
            drawn_group = tell(group, "get-drawn-coincident-group")
            if not exists_p(drawn_group):
                tell(setup.g_workspace_window, "draw-group", group)
            elif proposal_level > tell(drawn_group, "get-proposal-level"):
                tell(setup.g_workspace_window, "erase-group", drawn_group)
                tell(setup.g_workspace_window, "draw-group", group)
    tell(setup.g_workspace_window, "flush")
    return "done"
