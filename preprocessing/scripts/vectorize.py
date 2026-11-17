# Python 2.7. SySeVR's "Step 2: data preprocess", run with the authors' own scripts
# (Implementation/data_preprocess) in the order their README gives. The released scripts don't agree with each
# other on some file names and formats, and the small adapters below just connect them. Anything that can change a
# result is marked "Changes results" and is listed in our README.
# Usage: vectorize.py SLICE_DIR LABEL_DIR OUT_DIR     (run it from a copy of Implementation/data_preprocess)
import os, sys, pickle, shutil, time, json, resource
sys.path.insert(0, os.getcwd())

# Changes results (reproducibility): the paper's scripts list folders with os.listdir, whose order depends on the
# file system. That order feeds the seeded 80/20 shuffle and word2vec, so Windows (Docker Desktop) and Linux gave
# different results. Sorting every listing makes them the same everywhere.
_listdir = os.listdir
os.listdir = lambda path='.': sorted(_listdir(path))
# dealrawdata imports imblearn but never uses it, so an empty stand-in is enough.
sys.modules['imblearn'] = type(sys)('imblearn')
for m in ('imblearn.ensemble', 'imblearn.over_sampling'):
    mod = type(sys)(m); mod.BalanceCascade = mod.ADASYN = mod.SMOTE = None; sys.modules[m] = mod
import create_hash, delete_list, process_dataflow_func, create_w2vmodel, get_dl_input, dealrawdata

SLICES, LABELS, OUT = sys.argv[1:4]
# Changes results: create_w2vmodel.py trains word vectors of 30 numbers, but the released dealrawdata.py assumes 40.
VECTOR_DIM, MAXLEN = 30, 500
stats, times = {}, {}


def d(*p):
    path = os.path.join(OUT, *p)
    if not os.path.isdir(path): os.makedirs(path)
    return path + '/'


def timed(name, fn, *a):
    print('  ' + name); t = time.time(); r = fn(*a); times[name] = round(time.time() - t, 2); return r


def parse(path):
    """Splits a slice file the same way the paper's make_label_sard.make_label does."""
    sl = open(path).read().split('------------------------------')[:-1]
    if sl and sl[0] == '': del sl[0]
    if sl and sl[-1] in ('', '\n', '\r\n'): del sl[-1]
    out = []
    for s in sl:
        se = s.split('\n')
        if se[0] in ('\r', ''): del se[0]
        if se == []: continue
        if se[-1] == '': del se[-1]
        if se[-1] == '\r': del se[-1]
        out.append(se)
    return out


# 0. The paper's SARD folder layout (process_dataflow_func wants "SARD" in the slice path). Empty slice files
#    (no candidates of that kind) are left out, because the paper's create_hash crashes on them.
src = d('data_source', 'SARD')
for f in os.listdir(SLICES):
    if open(os.path.join(SLICES, f)).read().strip(): shutil.copy(os.path.join(SLICES, f), src)
stats['slices_in'] = {f: len(parse(src + f)) for f in sorted(os.listdir(src))}

# Adapter A: make_label_sard saves the labels as a list, but process_dataflow_func wants a dict keyed by slice header.
lab = d('label_source', 'SARD')
for f in sorted(os.listdir(src)):
    headers = [se[0] for se in parse(src + f)]
    labels = pickle.load(open(os.path.join(LABELS, f[:-4] + '_label.pkl'), 'rb'))
    assert len(headers) == len(labels), (f, len(headers), len(labels))
    assert len(set(headers)) == len(headers), f + ': duplicate slice headers'
    pickle.dump(dict(zip(headers, labels)), open(lab + f[:-4] + '_label.pkl', 'wb'))

# 1-2. Paper: hash every slice and list the exact duplicates to delete (within each slice file).
timed('create_hash', create_hash.get_hashs, src, d('hash_slices', 'SARD'))
timed('delete_list', delete_list.dedouble, d('hash_slices', 'SARD'), d('delete_list', 'SARD'))
# Adapter B: delete_list saves <name>.pkl, but process_dataflow_func opens <name>.txt.
dl = d('delete_list', 'SARD')
for f in os.listdir(dl):
    if f.endswith('.pkl'): shutil.copy(dl + f, dl + f[:-4] + '.txt')
stats['duplicates'] = {f: len(pickle.load(open(dl + f[:-4] + '.pkl', 'rb'))) for f in stats['slices_in']}

# 3. Paper: split into tokens and replace names with variable_N / func_N, one corpus folder per program.
corpus = d('corpus')
timed('process_dataflow_func', process_dataflow_func.get_sentences, src, lab, dl, corpus, True)
cnt, vul, toklen = {}, {}, []
for prog in os.listdir(corpus):
    for f in os.listdir(corpus + prog):
        c = pickle.load(open(corpus + prog + '/' + f, 'rb'))
        cnt[f] = cnt.get(f, 0) + len(c[0]); vul[f] = vul.get(f, 0) + sum(c[1]); toklen += [len(x) for x in c[0]]
stats['corpus_slices'] = cnt; stats['corpus_vulnerable'] = vul; stats['programs'] = len(os.listdir(corpus))
toklen.sort(); n = len(toklen)
stats['tokens_per_slice'] = dict(min=toklen[0], median=toklen[n // 2], p90=toklen[int(n * .9)], p99=toklen[int(n * .99)],
                                 max=toklen[-1], over_500=sum(t > MAXLEN for t in toklen))

# 4. Paper: train word2vec on the whole corpus (create_w2vmodel: size 30, skip-gram, 5 iterations, seed 1, 1 worker).
w2v = d('w2v_model') + 'wordmodel3'
timed('create_w2vmodel', create_w2vmodel.generate_w2vModel, [corpus], w2v)
from gensim.models.word2vec import Word2Vec
stats['vocabulary'] = len(Word2Vec.load(w2v).wv.vocab)

# 5. Paper: turn the tokens into vectors (get_dl_input), then split 80/20 by program (get_dldata, numpy seed 113).
# Adapter C: get_dldata picks files by the names "api", "arraysuse", "pointersuse" and "integeroverflow".
MODE_NAME = {'api_slices.pkl': 'api_slices.pkl', 'array_slices.pkl': 'arraysuse_slices.pkl',
             'pointer_slices.pkl': 'pointersuse_slices.pkl', 'expr_slices.pkl': 'integeroverflow_slices.pkl'}
vec = d('vector'); t = time.time(); print('  words -> vectors')
for prog in os.listdir(corpus):
    for f in os.listdir(corpus + prog):
        data = pickle.load(open(corpus + prog + '/' + f, 'rb'))
        data[0] = get_dl_input.generate_corpus(w2v, data[0])
        pickle.dump(data, open(d('vector', prog) + MODE_NAME[f], 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
times['get_dl_input_vectors'] = round(time.time() - t, 2)
timed('get_dldata_split', get_dl_input.get_dldata, vec, d('dl_input', 'train'), d('dl_input', 'test'))


# Changes results (test set): the released get_dldata only uses 2/8 of the test programs for pointer slices, and
# dealrawdata only keeps the "api" test files. We keep the paper's split (same shuffle, seed 113, first 80% of
# programs for training) and its training files as they are, but rebuild the test set from every slice of every
# test program.
def fixed_test(filepath, testpath, split=0.8, seed=113):
    import numpy as np
    folders = os.listdir(filepath); np.random.seed(seed); np.random.shuffle(folders)   # exactly what get_dldata does
    test_folders = folders[int(len(folders) * split):]
    shutil.rmtree(testpath); os.makedirs(testpath)
    for mode in ["api", "arraysuse", "pointersuse", "integeroverflow"]:
        test_set, ids = [[], [], [], [], [], []], []
        for folder in test_folders:
            for filename in os.listdir(filepath + folder + '/'):
                if mode in filename:
                    data = pickle.load(open(filepath + folder + '/' + filename, 'rb'))
                    ids += [folder] * len(data[1])
                    for k in range(5): test_set[k] = test_set[k] + data[k]
                    test_set[-1] = ids
        if test_set[0]:
            pickle.dump(test_set, open(testpath + mode + '_test.pkl', 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
    return len(test_folders)


stats['test_programs'] = timed('fixed_test_split', fixed_test, vec, d('dl_input', 'test'))


def count(path):
    r = {}
    for f in os.listdir(path):
        if f.endswith('.pkl'):
            x = pickle.load(open(path + f, 'rb')); r[f] = [len(x[1]), sum(x[1]), len(set(x[-1]))]
    return r


# 6. Paper: pad or cut every slice to 500 words around its focus (dealrawdata).
timed('dealrawdata', dealrawdata.dealrawdata, d('dl_input', 'train'), d('dl_input', 'test'),
      d('dl_input_shuffle', 'train'), d('dl_input_shuffle', 'test'), 16, MAXLEN, VECTOR_DIM)
# Changes results (test set, continued): dealrawdata skips test files without "api" in the name, so we pad/cut
# those here with the paper's own load_data_binary.
for f in os.listdir(d('dl_input', 'test')):
    if 'api' not in f:
        r = dealrawdata.load_data_binary(d('dl_input', 'test') + f, 16, maxlen=MAXLEN, vector_dim=VECTOR_DIM)
        pickle.dump(list(r), open(d('dl_input_shuffle', 'test') + f, 'wb'))
stats['final_train'] = count(d('dl_input_shuffle', 'train')); stats['final_test'] = count(d('dl_input_shuffle', 'test'))
for k in ('train', 'test'):
    v = stats['final_' + k].values()
    stats['total_' + k] = dict(slices=sum(x[0] for x in v), vulnerable=sum(x[1] for x in v))
stats['times_s'] = times
stats['peak_rss_mb'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
json.dump(stats, open(os.path.join(OUT, 'vectorize_stats.json'), 'w'), indent=1, sort_keys=True)
print(json.dumps(stats, indent=1, sort_keys=True))
