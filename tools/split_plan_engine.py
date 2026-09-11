#!/usr/bin/env python3
from pathlib import Path
import ast, argparse, hashlib

MOTION_FUNCS = {
    '_save_mouse_pos','_rf','_below','rand_range','_clamp','tuned_wind',
    'build_range_profile','sample_profile','_poly_len','windmouse',
    'resample_variable','assign_dynamic_delays','curve_height_ratio','_ray_to_edge',
    'build_arc','plan_move','_build_leg','_exec_rmouse',
}
MOTION_ASSIGNS = {'_DEFAULT_CFG'}
TYPING_FUNCS = {'_below','rand_range','_clamp','_qwerty_neighbor','_split_punct','plan_typing'}
TYPING_ASSIGNS = {'_QWERTY_ROWS','_PUNCT'}
MOVED_FUNCS = (MOTION_FUNCS | TYPING_FUNCS) - {'_below','rand_range','_clamp','_save_mouse_pos'}
MOVED_ASSIGNS = MOTION_ASSIGNS | TYPING_ASSIGNS

class Clean(ast.NodeTransformer):
    def _clean(self, node):
        self.generic_visit(node)
        if getattr(node, 'body', None) and isinstance(node.body[0], ast.Expr):
            v = node.body[0].value
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                node.body = node.body[1:]
        if hasattr(node, 'body') and not node.body:
            node.body = [ast.Pass()]
        return node
    visit_Module = _clean
    visit_ClassDef = _clean
    visit_FunctionDef = _clean
    visit_AsyncFunctionDef = _clean

def assigned_names(node):
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
        return set()
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return {t.id for t in targets if isinstance(t, ast.Name)}

def clean_unparse(nodes):
    mod = ast.Module(body=nodes, type_ignores=[])
    mod = Clean().visit(mod)
    ast.fix_missing_locations(mod)
    return ast.unparse(mod) + '\n'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('outdir')
    a=ap.parse_args()
    source=Path(a.source)
    out=Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    tree=ast.parse(source.read_text(encoding='utf-8'))
    imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
    motion=[]; typing=[]; core=[]
    for n in tree.body:
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            core.append(n)
        elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            if n.name in MOTION_FUNCS: motion.append(n)
            if n.name in TYPING_FUNCS: typing.append(n)
            if n.name not in MOVED_FUNCS: core.append(n)
        elif isinstance(n,(ast.Assign,ast.AnnAssign)):
            names=assigned_names(n)
            if names & MOTION_ASSIGNS: motion.append(n)
            if names & TYPING_ASSIGNS: typing.append(n)
            if not (names & MOVED_ASSIGNS): core.append(n)
        else:
            core.append(n)
    std_imports=[]
    for n in imports:
        names={x.name for x in n.names}
        if names & {'time','math','random'}: std_imports.append(n)
    motion_text = '# Generated from canonical plan_engine.py; do not hand-edit.\n' + clean_unparse(std_imports + motion)
    typing_text = '# Generated from canonical plan_engine.py; do not hand-edit.\n' + clean_unparse(std_imports + typing)
    wrappers=ast.parse('''\n_motion_module = None\n_typing_module = None\n\ndef _exec_rmouse(prm, ctx, pauses, pos, target=None):\n    global _motion_module\n    if _motion_module is None:\n        import plan_motion as _motion_module\n        _motion_module.PlanAbort = PlanAbort  # PLAN2_H5_CONTROL_FIX: one shared abort type\n    return _motion_module._exec_rmouse(prm, ctx, pauses, pos, target)\n\ndef plan_typing(text, prm):\n    global _typing_module\n    if _typing_module is None:\n        import plan_typing as _typing_module\n    return _typing_module.plan_typing(text, prm)\n''').body
    core_text = '# Generated memory-fit core from canonical plan_engine.py; do not hand-edit.\n' + clean_unparse(core + wrappers)
    files={'plan_engine.py':core_text,'plan_motion.py':motion_text,'plan_typing.py':typing_text}
    for name,text in files.items():
        compile(text,name,'exec')
        (out/name).write_text(text,encoding='utf-8',newline='\n')
        print(name, len(text.encode()), hashlib.sha256(text.encode()).hexdigest())
    total=sum(len(x.encode()) for x in files.values())
    print('total',total)

if __name__=='__main__': main()
