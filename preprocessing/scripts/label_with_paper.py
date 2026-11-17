# Python 2.7. Runs the paper's make_label_sard.main() as it is, with one guard added.
# The paper's make_label() crashes with an IndexError on a slice file that has no slices. That happens when the
# chosen test cases have no candidates of some kind (no arithmetic expressions, for example). For such a file we
# return an empty label list; every other file is labelled by the paper's own make_label().
import os, sys
sys.path.insert(0, os.getcwd())
import make_label_sard as paper

_orig = paper.make_label
def _guarded(path, _dict):
    if not open(path).read().strip():
        print(path + ': no slices of this kind, empty label list')
        return []
    return _orig(path, _dict)
paper.make_label = _guarded
paper.main()
