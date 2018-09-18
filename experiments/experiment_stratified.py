import numpy as np
import random
import pandas as pd

from tilapia.builder import build_model
from tilapia.ia.utils import weight_adaptation, weights_to_matrix, prep_words
from experiments.data import read_elp_format
from itertools import product
from tqdm import tqdm
from copy import deepcopy
from binningsampler import BinnedSampler


def accuracy(words, results, threshold=.7):
    """Compute accuracy."""
    score = []

    for w, result in zip(words, results):
        result = result['orthography']
        if not result[-1]:
            score.append(False)
            continue
        keys, values = zip(*result[-1].items())
        if np.max(values) < threshold:
            score.append(False)
            continue
        if keys[np.argmax(values)] == w:
            score.append(True)
            continue
        else:
            score.append(False)

    return np.sum(score), score


if __name__ == "__main__":

    header = []
    results = []
    random.seed(44)

    threshold = .7

    path = "../../corpora/lexicon_projects/elp-items.csv"

    words = np.array(list(read_elp_format(path, lengths=list(range(3, 11)))))

    num_to_sample = len(words) // 4
    freqs = [x['frequency'] + 1 for x in words]
    freqs = np.log10(freqs)

    sampler = BinnedSampler(words, freqs)
    total = (2 ** 3) * 100
    n_cyc = 350

    for idx, (le, ne, spa) in enumerate(product([True, False],
                                                [True, False],
                                                [True, False])):

        length_adaptation = le
        negative_evidence = ne
        space_character = spa

        np.random.seed(44)

        for idx_2 in tqdm(range(100)):

            print("{} of {}".format((idx * 100) + idx_2, total))

            w = deepcopy(sampler.sample(num_to_sample))

            logfreq = np.log10([x['frequency'] for x in w])
            lengths = [len(x['orthography']) for x in w]
            rt = np.array([x['rt'] for x in w])

            if length_adaptation:
                max_len = max([len(x['orthography']) for x in w])
            else:
                max_len = 4

            m = max([len(x['orthography']) for x in w])
            if space_character:
                for w_ in w:
                    w_['orthography'] = w_['orthography'].ljust(m)

            inputs = ['features']
            if negative_evidence:
                inputs.append('features_neg')

            w = prep_words(w)
            matrix, names = weights_to_matrix(weight_adaptation(max_len))

            rla = {k: 'global' for k in names}
            rla['orthography'] = 'frequency'

            s = build_model(w,
                            names,
                            matrix,
                            rla,
                            -.05,
                            step_size=.5,
                            outputs=('orthography',),
                            inputs=inputs)

            result = s.activate_bunch(w,
                                      max_cycles=n_cyc,
                                      threshold=threshold,
                                      strict=False)

            cycles = np.array([len(x['orthography']) for x in result])
            right = cycles == n_cyc
            cycles[right] = -1
            for x, word in zip(result, w):
                results.append([word['orthography'],
                                (idx * 100) + idx_2,
                                word['rt'],
                                word['frequency'],
                                len(x),
                                le,
                                ne,
                                spa])

    df = pd.DataFrame(results, columns=header)
    df.to_csv("tilapia_experiment_stratified.csv", sep=",")
