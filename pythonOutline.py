import os
import sys

import sublime
import sublime_plugin

sys.path.append(os.path.dirname(__file__))

import classBrowser  # noqa e402


class PythonOutlineCommand(sublime_plugin.TextCommand):
    
    def run(self, edit):
        '''
            folds = [
                (1, 5),
                (18, 22),
                (14, 17),
                (6 ,13),
                (23, 24),
            ]
        '''
        
        # Pullout the start and end lines of each method and function into pairs.
        structure = classBrowser._readmodule(self.view.substr(sublime.Region(0, self.view.size())))
        folds = []
        for a, b in structure.items():
            if isinstance(b, classBrowser.Class):
                for m in b.methods:
                    folds.append(( b.methods[m], b.methodends[m]) )
            else:
                folds.append(( b.lineno, b.linenoend ))
        
        lines = self.view.split_by_newlines( sublime.Region(0, self.view.size()) )
        
        # Since classBrowswer returns lines as 1-based (human-readable), the
        # first line is fine (we want to see the def) but the end needs to offset.
        for start, end in folds[:-1]:
            endRegion = lines[end-1]
            
            self.view.fold( sublime.Region( lines[start].a - 1, endRegion.b )  )
        
        # Handle if the last line is at the end
        start, end = folds[-1]
        if end < len(lines):
            endRegion = lines[end-1]
        else:
            endRegion = lines[-1]
        self.view.fold( sublime.Region( lines[start].a - 1, endRegion.b )  )
            
