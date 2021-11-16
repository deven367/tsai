# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/010_data.validation.ipynb (unless otherwise specified).

__all__ = ['check_overlap', 'check_splits_overlap', 'leakage_finder', 'balance_idx', 'TrainValidTestSplitter',
           'plot_splits', 'get_splits', 'TSSplitter', 'TimeSplitter', 'get_predefined_splits', 'combine_split_data',
           'get_splits_len']

# Cell
from ..imports import *
from ..utils import *

# Cell
from sklearn.model_selection import train_test_split, KFold, StratifiedKFold
from imblearn.over_sampling import RandomOverSampler

# Cell
def check_overlap(a, b, c=None):
    a = toarray(a)
    b = toarray(b)
    overlap_ab = np.isin(a, b)
    if c is None:
        if isinstance(overlap_ab[0], (list, L, np.ndarray, torch.Tensor)):  overlap_ab = overlap_ab[0]
        if not any(overlap_ab): return False
        else: return a[overlap_ab].tolist()
    else:
        c = toarray(c)
        overlap_ac = np.isin(a, c)
        if isinstance(overlap_ac[0], (list, L, np.ndarray, torch.Tensor)):  overlap_ac = overlap_ac[0]
        overlap_bc = np.isin(b, c)
        if isinstance(overlap_bc[0], (list, L, np.ndarray, torch.Tensor)):  overlap_bc = overlap_bc[0]
        if not any(overlap_ab) and not any(overlap_ac) and not any(overlap_bc): return False
        else: return a[overlap_ab].tolist(), a[overlap_ac].tolist(), b[overlap_bc].tolist()

def check_splits_overlap(splits):
    return [check_overlap(*_splits) for _splits in splits] if is_listy(splits[0][0]) else [check_overlap(*splits)]

def leakage_finder(*splits, verbose=True):
    '''You can pass splits as a tuple, or train, valid, ...'''
    splits = L(*splits)
    overlaps = 0
    for i in range(len(splits)):
        for j in range(i + 1, len(splits)):
            overlap = check_overlap(splits[i], splits[j])
            if overlap:
                pv(f'overlap between splits [{i}, {j}] {overlap}', verbose)
                overlaps += 1
    assert overlaps == 0, 'Please, review your splits!'


def balance_idx(o, shuffle=False, random_state=None, verbose=False):
    if isinstance(o, list): o = L(o)
    idx_ = np.arange(len(o)).reshape(-1, 1)
    ros = RandomOverSampler(random_state=random_state)
    resampled_idxs, _ = ros.fit_resample(idx_, np.asarray(o))
    new_idx = L(resampled_idxs.reshape(-1,).tolist())
    if shuffle: new_idx = random_shuffle(new_idx)
    return new_idx

# Cell
def TrainValidTestSplitter(n_splits:int=1, valid_size:Union[float, int]=0.2, test_size:Union[float, int]=0., train_only:bool=False,
                           stratify:bool=True, balance:bool=False, shuffle:bool=True, random_state:Union[None, int]=None, verbose:bool=False, **kwargs):
    "Split `items` into random train, valid (and test optional) subsets."

    if not shuffle and stratify and not train_only:
        pv('stratify set to False because shuffle=False. If you want to stratify set shuffle=True', verbose)
        stratify = False

    def _inner(o, **kwargs):
        if stratify:
            _, unique_counts = np.unique(o, return_counts=True)
            if np.min(unique_counts) >= 2 and np.min(unique_counts) >= n_splits: stratify_ = stratify
            elif np.min(unique_counts) < n_splits:
                stratify_ = False
                pv(f'stratify set to False as n_splits={n_splits} cannot be greater than the min number of members in each class ({np.min(unique_counts)}).',
                   verbose)
            else:
                stratify_ = False
                pv('stratify set to False as the least populated class in o has only 1 member, which is too few.', verbose)
        else: stratify_ = False
        vs = 0 if train_only else 1. / n_splits if n_splits > 1 else int(valid_size * len(o)) if isinstance(valid_size, float) else valid_size
        if test_size:
            ts = int(test_size * len(o)) if isinstance(test_size, float) else test_size
            train_valid, test = train_test_split(range(len(o)), test_size=ts, stratify=o if stratify_ else None, shuffle=shuffle,
                                                 random_state=random_state, **kwargs)
            test = toL(test)
            if shuffle: test = random_shuffle(test, random_state)
            if vs == 0:
                train, _ = RandomSplitter(0, seed=random_state)(o[train_valid])
                train = toL(train)
                if balance: train = train[balance_idx(o[train], random_state=random_state)]
                if shuffle: train = random_shuffle(train, random_state)
                train_ = L(L([train]) * n_splits) if n_splits > 1 else train
                valid_ = L(L([train]) * n_splits) if n_splits > 1 else train
                test_ = L(L([test]) * n_splits) if n_splits > 1 else test
                if n_splits > 1:
                    return [split for split in itemify(train_, valid_, test_)]
                else:
                    return train_, valid_, test_
            elif n_splits > 1:
                if stratify_:
                    splits = StratifiedKFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state).split(np.arange(len(train_valid)), o[train_valid])
                else:
                    splits = KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state).split(np.arange(len(train_valid)))
                train_, valid_ = L([]), L([])
                for train, valid in splits:
                    train, valid = toL(train), toL(valid)
                    if balance: train = train[balance_idx(o[train], random_state=random_state)]
                    if shuffle:
                        train = random_shuffle(train, random_state)
                        valid = random_shuffle(valid, random_state)
                    train_.append(L(L(train_valid)[train]))
                    valid_.append(L(L(train_valid)[valid]))
                test_ = L(L([test]) * n_splits)
                return [split for split in itemify(train_, valid_, test_)]
            else:
                train, valid = train_test_split(range(len(train_valid)), test_size=vs, random_state=random_state,
                                                stratify=o[train_valid] if stratify_ else None, shuffle=shuffle, **kwargs)
                train, valid = toL(train), toL(valid)
                if balance: train = train[balance_idx(o[train], random_state=random_state)]
                if shuffle:
                    train = random_shuffle(train, random_state)
                    valid = random_shuffle(valid, random_state)
                return (L(L(train_valid)[train]), L(L(train_valid)[valid]),  test)
        else:
            if vs == 0:
                train, _ = RandomSplitter(0, seed=random_state)(o)
                train = toL(train)
                if balance: train = train[balance_idx(o[train], random_state=random_state)]
                if shuffle: train = random_shuffle(train, random_state)
                train_ = L(L([train]) * n_splits) if n_splits > 1 else train
                valid_ = L(L([train]) * n_splits) if n_splits > 1 else train
                if n_splits > 1:
                    return [split for split in itemify(train_, valid_)]
                else:
                    return (train_, valid_)
            elif n_splits > 1:
                if stratify_: splits = StratifiedKFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state).split(np.arange(len(o)), o)
                else: splits = KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state).split(np.arange(len(o)))
                train_, valid_ = L([]), L([])
                for train, valid in splits:
                    train, valid = toL(train), toL(valid)
                    if balance: train = train[balance_idx(o[train], random_state=random_state)]
                    if shuffle:
                        train = random_shuffle(train, random_state)
                        valid = random_shuffle(valid, random_state)
                    if not isinstance(train, (list, L)):  train = train.tolist()
                    if not isinstance(valid, (list, L)):  valid = valid.tolist()
                    train_.append(L(train))
                    valid_.append(L(L(valid)))
                return [split for split in itemify(train_, valid_)]
            else:
                train, valid = train_test_split(range(len(o)), test_size=vs, random_state=random_state, stratify=o if stratify_ else None,
                                                shuffle=shuffle, **kwargs)
                train, valid = toL(train), toL(valid)
                if balance: train = train[balance_idx(o[train], random_state=random_state)]
                return train, valid
    return _inner

# Cell
from matplotlib.patches import Patch

def plot_splits(splits):
    _max = 0
    _splits = 0
    for i, split in enumerate(splits):
        if is_listy(split[0]):
            for j, s in enumerate(split):
                _max = max(_max, array(s).max())
                _splits += 1
        else:
            _max = max(_max, array(split).max())
            _splits += 1
    _splits = [splits] if not is_listy(split[0]) else splits
    v = np.zeros((len(_splits), _max + 1))
    for i, split in enumerate(_splits):
        if is_listy(split[0]):
            for j, s in enumerate(split):
                v[i, s] = 1 + j
        else: v[i, split] = 1 + i
    vals = np.unique(v)
    plt.figure(figsize=(16, len(_splits)/2))
    if len(vals) == 1:
        v = np.ones((len(_splits), _max + 1))
        plt.pcolormesh(v, color='blue')
        legend_elements = [Patch(facecolor='blue', label='Train')]
        plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
    else:
        colors = L(['gainsboro', 'blue', 'limegreen', 'red'])[vals]
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list('', colors)
        plt.pcolormesh(v, cmap=cmap)
        legend_elements = L([
            Patch(facecolor='gainsboro', label='None'),
            Patch(facecolor='blue', label='Train'),
            Patch(facecolor='limegreen', label='Valid'),
            Patch(facecolor='red', label='Test')])[vals]
        plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.title('Split distribution')
    plt.yticks(ticks=np.arange(.5, len(_splits)+.5, 1.0), labels=np.arange(1, len(_splits)+1, 1.0).astype(int))
    plt.gca().invert_yaxis()
    plt.show()

# Cell
def get_splits(o, n_splits:int=1, valid_size:float=0.2, test_size:float=0., train_only:bool=False, train_size:Union[None, float, int]=None, balance:bool=False,
               shuffle:bool=True, stratify:bool=True, check_splits:bool=True, random_state:Union[None, int]=None, show_plot:bool=True, verbose:bool=False):
    '''Arguments:
        o            : object to which splits will be applied, usually target.
        n_splits     : number of folds. Must be an int >= 1.
        valid_size   : size of validation set. Only used if n_splits = 1. If n_splits > 1 valid_size = (1. - test_size) / n_splits.
        test_size    : size of test set. Default = 0.
        train_only   : if True valid set == train set. This may be useful for debugging purposes.
        train_size   : size of the train set used. Default = None (the remainder after assigning both valid and test).
                        Useful for to get learning curves with different train sizes or get a small batch to debug a neural net.
        balance      : whether to balance data so that train always contain the same number of items per class.
        shuffle      : whether to shuffle data before splitting into batches. Note that the samples within each split will be shuffle.
        stratify     : whether to create folds preserving the percentage of samples for each class.
        check_splits : whether to perform leakage and completion checks.
        random_state : when shuffle is True, random_state affects the ordering of the indices. Pass an int for reproducible output.
        show_plot    : plot the split distribution
    '''
    if n_splits == 1 and valid_size == 0. and  test_size == 0.: train_only = True
    if balance: stratify = True
    splits = TrainValidTestSplitter(n_splits, valid_size=valid_size, test_size=test_size, train_only=train_only, stratify=stratify,
                                      balance=balance, shuffle=shuffle, random_state=random_state, verbose=verbose)(o)
    if check_splits:
        if train_only or (n_splits == 1 and valid_size == 0): print('valid == train')
        elif n_splits > 1:
            for i in range(n_splits):
                leakage_finder([*splits[i]], verbose=True)
                cum_len = 0
                for split in splits[i]: cum_len += len(split)
                if not balance: assert len(o) == cum_len, f'len(o)={len(o)} while cum_len={cum_len}'
        else:
            leakage_finder([splits], verbose=True)
            cum_len = 0
            if not isinstance(splits[0], Integral):
                for split in splits: cum_len += len(split)
            else: cum_len += len(splits)
            if not balance: assert len(o) == cum_len, f'len(o)={len(o)} while cum_len={cum_len}'
    if train_size is not None and train_size != 1: # train_size=1 legacy
        if n_splits > 1:
            splits = list(splits)
            for i in range(n_splits):
                splits[i] = list(splits[i])
                if isinstance(train_size, Integral):
                    n_train_samples = train_size
                elif train_size > 0 and train_size < 1:
                    n_train_samples = int(len(splits[i][0]) * train_size)
                splits[i][0] = L(np.random.choice(splits[i][0], n_train_samples, False).tolist())
                if train_only:
                    if valid_size != 0: splits[i][1] = splits[i][0]
                    if test_size != 0: splits[i][2] = splits[i][0]
                splits[i] = tuple(splits[i])
            splits = tuple(splits)
        else:
            splits = list(splits)
            if isinstance(train_size, Integral):
                n_train_samples = train_size
            elif train_size > 0 and train_size < 1:
                n_train_samples = int(len(splits[0]) * train_size)
            splits[0] = L(np.random.choice(splits[0], n_train_samples, False).tolist())
            if train_only:
                if valid_size != 0: splits[1] = splits[0]
                if test_size != 0: splits[2] = splits[0]
            splits = tuple(splits)
    if show_plot: plot_splits(splits)
    return splits

# Cell
def TSSplitter(valid_size:Union[int, float]=0.2, test_size:Union[int, float]=0., show_plot:bool=True):
    "Create function that splits `items` between train/val with `valid_size` without shuffling data."
    def _inner(o):
        valid_cut = valid_size if isinstance(valid_size, Integral) else int(round(valid_size * len(o)))
        if test_size:
            test_cut = test_size if isinstance(test_size, Integral) else int(round(test_size * len(o)))
        idx = np.arange(len(o))
        if test_size:
            splits = L(idx[:-valid_cut - test_cut].tolist()), L(idx[-valid_cut - test_cut: - test_cut].tolist()), L(idx[-test_cut:].tolist())
        else:
            splits = L(idx[:-valid_cut].tolist()), L(idx[-valid_cut:].tolist())
        if show_plot:
            if len(o) > 1_000_000:
                warnings.warn('the splits are too large to be plotted')
            else:
                plot_splits(splits)
        return splits
    return _inner

TimeSplitter = TSSplitter

# Cell
def get_predefined_splits(*xs):
    '''xs is a list with X_train, X_valid, ...'''
    splits_ = []
    start = 0
    for x in xs:
        splits_.append(L(list(np.arange(start, start + len(x)))))
        start += len(x)
    return tuple(splits_)

def combine_split_data(xs, ys=None):
    '''xs is a list with X_train, X_valid, .... ys is None or a list with y_train, y_valid, .... '''
    xs = [to3d(x) for x in xs]
    splits = get_predefined_splits(*xs)
    if ys is None: return concat(*xs), None, splits
    else: return concat(*xs), concat(*ys), splits

# Cell
def get_splits_len(splits):
    _len = []
    for split in splits:
        if isinstance(split[0], (list, L, tuple)):  _len.append([len(s) for s in split])
        else: _len.append(len(split))
    return _len