# -*- coding: utf-8 -*-
# file: word2vec.py
# time: 2021/7/30
# author: yangheng <yangheng@m.scnu.edu.cn>
# github: https://github.com/yangheng95
# Copyright (C) 2021. All Rights Reserved.

import os
import time

from findfile import find_files
from gensim.models import Word2Vec

# from gensim.models.word2vec import LineSentence
import DaNuoYi.global_config


def train_word2vec(workers=1):
    '''
    LineSentence(inp)：The format is simple: one sentence = one line; words are preprocessed and separated by spaces.
    size：is the vector dimension of each word;
    window：is the size of the context scan window during word vector training,
            and the window is 5 to consider the first 5 words and the last 5 words;
    min-count：Set the minimum frequency, the default is 5, if a word appears in the document less than 5 times,
               it will be discarded;
    workers：is the number of training processes (a more precise explanation is needed, please correct me),
             the default is the number of processor cores of the currently running machine.
             Just remember these parameters first.
    sg ({0, 1}, optional) – Model training algorithm: 1: skip-gram; 0: CBOW
    alpha (float, optional) – initial learning rate
    iter (int, optional) – The number of iterations, the default is 5
    '''
    in_corpus_path = find_files('injection_cases', key='.txt', recursive=True)
    while len(in_corpus_path) < 18:
        time.sleep(global_config.RETRY_TIME)
        in_corpus_path = find_files('injection_cases', key='.txt', recursive=True)

    in_corpus = []
    for p in in_corpus_path:
        fin = open(p, mode='r', encoding='utf8')
        in_corpus.extend([line.split('$BYPASS_LABEL$')[0].strip() for line in fin.readlines()])
        fin.close()

    print('Training word2vec ...')

    save_path = os.path.join(global_config.PROJECT_PATH, 'runtime_materials/word2vec')
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    model = Word2Vec(in_corpus, vector_size=128, window=5, min_count=5, sg=1, workers=workers, epochs=50)
    model.wv.save_word2vec_format(os.path.join(save_path, 'w2v.txt'), binary=False)  # 不以C语言可以解析的形式存储词向量
    model.save(os.path.join(save_path, 'w2v.model'))
    print('Word2vec training done ...')
