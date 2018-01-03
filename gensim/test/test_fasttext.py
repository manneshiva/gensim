#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import unittest
import os
import struct

import numpy as np

from gensim import utils
from gensim.models.word2vec import LineSentence, Word2VecKeyedVectors
from gensim.models.fasttext import FastText as FT_gensim, FastTextKeyedVectors
from gensim.test.utils import datapath, get_tmpfile, common_texts as sentences

logger = logging.getLogger(__name__)

IS_WIN32 = (os.name == "nt") and (struct.calcsize('P') * 8 == 32)


class LeeCorpus(object):
    def __iter__(self):
        with open(datapath('lee_background.cor')) as f:
            for line in f:
                yield utils.simple_preprocess(line)


list_corpus = list(LeeCorpus())

new_sentences = [
    ['computer', 'artificial', 'intelligence'],
    ['artificial', 'trees'],
    ['human', 'intelligence'],
    ['artificial', 'graph'],
    ['intelligence'],
    ['artificial', 'intelligence', 'system']
]


class TestFastTextModel(unittest.TestCase):

    def setUp(self):
        ft_home = os.environ.get('FT_HOME', None)
        self.ft_path = os.path.join(ft_home, 'fasttext') if ft_home else None
        self.test_model_file = datapath('lee_fasttext')
        self.test_model = FT_gensim.load_fasttext_format(self.test_model_file)
        self.test_new_model_file = datapath('lee_fasttext_new')

    def test_training(self):
        model = FT_gensim(size=10, min_count=1, hs=1, negative=0, seed=42, workers=1)
        model.build_vocab(sentences)
        self.model_sanity(model)

        model.train(sentences, total_examples=model.corpus_count, epochs=model.iter)
        sims = model.wv.most_similar('graph', topn=10)

        self.assertEqual(model.wv.vectors.shape, (12, 10))
        self.assertEqual(len(model.wv.vocab), 12)
        self.assertEqual(model.wv.vectors_vocab.shape[1], 10)
        self.assertEqual(model.wv.vectors_ngrams.shape[1], 10)
        self.model_sanity(model)

        # test querying for "most similar" by vector
        graph_vector = model.wv.vectors_norm[model.wv.vocab['graph'].index]
        sims2 = model.wv.most_similar(positive=[graph_vector], topn=11)
        sims2 = [(w, sim) for w, sim in sims2 if w != 'graph']  # ignore 'graph' itself
        self.assertEqual(sims, sims2)

        # build vocab and train in one step; must be the same as above
        model2 = FT_gensim(sentences, size=10, min_count=1, hs=1, negative=0, seed=42, workers=1)
        self.models_equal(model, model2)

        # verify oov-word vector retrieval
        invocab_vec = model['minors']  # invocab word
        self.assertEqual(len(invocab_vec), 10)

        oov_vec = model['minor']  # oov word
        self.assertEqual(len(oov_vec), 10)

    def models_equal(self, model, model2):
        self.assertEqual(len(model.wv.vocab), len(model2.wv.vocab))
        self.assertEqual(model.trainables.num_ngram_vectors, model2.trainables.num_ngram_vectors)
        self.assertTrue(np.allclose(model.wv.vectors_vocab, model2.wv.vectors_vocab))
        self.assertTrue(np.allclose(model.wv.vectors_ngrams, model2.wv.vectors_ngrams))
        self.assertTrue(np.allclose(model.wv.vectors, model2.wv.vectors))
        if model.hs:
            self.assertTrue(np.allclose(model.trainables.syn1, model2.trainables.syn1))
        if model.negative:
            self.assertTrue(np.allclose(model.trainables.syn1neg, model2.trainables.syn1neg))
        most_common_word = max(model.wv.vocab.items(), key=lambda item: item[1].count)[0]
        self.assertTrue(np.allclose(model[most_common_word], model2[most_common_word]))

    @unittest.skipIf(IS_WIN32, "avoid memory error with Appveyor x32")
    def test_persistence(self):
        tmpf = get_tmpfile('gensim_fasttext.tst')
        model = FT_gensim(sentences, min_count=1)
        model.save(tmpf)
        self.models_equal(model, FT_gensim.load(tmpf))
        #  test persistence of the KeyedVectors of a model
        wv = model.wv
        wv.save(tmpf)
        loaded_wv = FastTextKeyedVectors.load(tmpf)
        self.assertTrue(np.allclose(wv.vectors_ngrams, loaded_wv.vectors_ngrams))
        self.assertEqual(len(wv.vocab), len(loaded_wv.vocab))
        self.assertEqual(len(wv.ngrams), len(loaded_wv.ngrams))

    @unittest.skipIf(IS_WIN32, "avoid memory error with Appveyor x32")
    def test_norm_vectors_not_saved(self):
        tmpf = get_tmpfile('gensim_fasttext.tst')
        model = FT_gensim(sentences, min_count=1)
        model.init_sims()
        model.save(tmpf)
        loaded_model = FT_gensim.load(tmpf)
        self.assertTrue(loaded_model.wv.vectors_norm is None)
        self.assertTrue(loaded_model.wv.vectors_ngrams_norm is None)

        wv = model.wv
        wv.save(tmpf)
        loaded_kv = FastTextKeyedVectors.load(tmpf)
        self.assertTrue(loaded_kv.vectors_norm is None)
        self.assertTrue(loaded_kv.vectors_ngrams_norm is None)

    def model_sanity(self, model):
        self.assertEqual(model.wv.vectors.shape, (len(model.wv.vocab), model.vector_size))
        self.assertEqual(model.wv.vectors_vocab.shape, (len(model.wv.vocab), model.vector_size))
        self.assertEqual(model.wv.vectors_ngrams.shape, (model.trainables.num_ngram_vectors, model.vector_size))

    def test_load_fasttext_format(self):
        try:
            model = FT_gensim.load_fasttext_format(self.test_model_file)
        except Exception as exc:
            self.fail('Unable to load FastText model from file %s: %s' % (self.test_model_file, exc))
        vocab_size, model_size = 1762, 10
        self.assertEqual(model.wv.vectors.shape, (vocab_size, model_size))
        self.assertEqual(len(model.wv.vocab), vocab_size, model_size)
        self.assertEqual(model.wv.vectors_ngrams.shape, (model.trainables.num_ngram_vectors, model_size))

        expected_vec = [
            -0.57144,
            -0.0085561,
            0.15748,
            -0.67855,
            -0.25459,
            -0.58077,
            -0.09913,
            1.1447,
            0.23418,
            0.060007
        ]  # obtained using ./fasttext print-word-vectors lee_fasttext_new.bin
        self.assertTrue(np.allclose(model["hundred"], expected_vec, atol=1e-4))

        # vector for oov words are slightly different from original FastText due to discarding unused ngrams
        # obtained using a modified version of ./fasttext print-word-vectors lee_fasttext_new.bin
        expected_vec_oov = [
            -0.23825,
            -0.58482,
            -0.22276,
            -0.41215,
            0.91015,
            -1.6786,
            -0.26724,
            0.58818,
            0.57828,
            0.75801
        ]
        self.assertTrue(np.allclose(model["rejection"], expected_vec_oov, atol=1e-4))

        self.assertEqual(model.vocabulary.min_count, 5)
        self.assertEqual(model.window, 5)
        self.assertEqual(model.iter, 5)
        self.assertEqual(model.negative, 5)
        self.assertEqual(model.vocabulary.sample, 0.0001)
        self.assertEqual(model.trainables.bucket, 1000)
        self.assertEqual(model.wv.max_n, 6)
        self.assertEqual(model.wv.min_n, 3)
        self.assertEqual(model.wv.vectors.shape, (len(model.wv.vocab), model.vector_size))
        self.assertEqual(model.wv.vectors_ngrams.shape, (model.trainables.num_ngram_vectors, model.vector_size))

    def test_load_fasttext_new_format(self):
        try:
            new_model = FT_gensim.load_fasttext_format(self.test_new_model_file)
        except Exception as exc:
            self.fail('Unable to load FastText model from file %s: %s' % (self.test_new_model_file, exc))
        vocab_size, model_size = 1763, 10
        self.assertEqual(new_model.wv.vectors.shape, (vocab_size, model_size))
        self.assertEqual(len(new_model.wv.vocab), vocab_size, model_size)
        self.assertEqual(new_model.wv.vectors_ngrams.shape, (new_model.trainables.num_ngram_vectors, model_size))

        expected_vec = [
            -0.025627,
            -0.11448,
            0.18116,
            -0.96779,
            0.2532,
            -0.93224,
            0.3929,
            0.12679,
            -0.19685,
            -0.13179
        ]  # obtained using ./fasttext print-word-vectors lee_fasttext_new.bin
        self.assertTrue(np.allclose(new_model["hundred"], expected_vec, atol=1e-4))

        # vector for oov words are slightly different from original FastText due to discarding unused ngrams
        # obtained using a modified version of ./fasttext print-word-vectors lee_fasttext_new.bin
        expected_vec_oov = [
            -0.53378,
            -0.19,
            0.013482,
            -0.86767,
            -0.21684,
            -0.89928,
            0.45124,
            0.18025,
            -0.14128,
            0.22508
        ]
        self.assertTrue(np.allclose(new_model["rejection"], expected_vec_oov, atol=1e-4))

        self.assertEqual(new_model.vocabulary.min_count, 5)
        self.assertEqual(new_model.window, 5)
        self.assertEqual(new_model.iter, 5)
        self.assertEqual(new_model.negative, 5)
        self.assertEqual(new_model.vocabulary.sample, 0.0001)
        self.assertEqual(new_model.trainables.bucket, 1000)
        self.assertEqual(new_model.wv.max_n, 6)
        self.assertEqual(new_model.wv.min_n, 3)
        self.assertEqual(new_model.wv.vectors.shape, (len(new_model.wv.vocab), new_model.vector_size))
        self.assertEqual(new_model.wv.vectors_ngrams.shape, (new_model.trainables.num_ngram_vectors, new_model.vector_size))

    def test_load_model_supervised(self):
        with self.assertRaises(NotImplementedError):
            FT_gensim.load_fasttext_format(datapath('pang_lee_polarity_fasttext'))

    def test_load_model_with_non_ascii_vocab(self):
        model = FT_gensim.load_fasttext_format(datapath('non_ascii_fasttext'))
        self.assertTrue(u'který' in model)
        try:
            model[u'který']
        except UnicodeDecodeError:
            self.fail('Unable to access vector for utf8 encoded non-ascii word')

    def test_load_model_non_utf8_encoding(self):
        model = FT_gensim.load_fasttext_format(datapath('cp852_fasttext'), encoding='cp852')
        self.assertTrue(u'který' in model)
        try:
            model[u'který']
        except KeyError:
            self.fail('Unable to access vector for cp-852 word')

    def test_n_similarity(self):
        # In vocab, sanity check
        self.assertTrue(np.allclose(self.test_model.wv.n_similarity(['the', 'and'], ['and', 'the']), 1.0))
        self.assertEqual(self.test_model.wv.n_similarity(['the'], ['and']), self.test_model.wv.n_similarity(['and'], ['the']))
        # Out of vocab check
        self.assertTrue(np.allclose(self.test_model.wv.n_similarity(['night', 'nights'], ['nights', 'night']), 1.0))
        self.assertEqual(
            self.test_model.wv.n_similarity(['night'], ['nights']), self.test_model.wv.n_similarity(['nights'], ['night'])
        )

    def test_similarity(self):
        # In vocab, sanity check
        self.assertTrue(np.allclose(self.test_model.wv.similarity('the', 'the'), 1.0))
        self.assertEqual(self.test_model.wv.similarity('the', 'and'), self.test_model.wv.similarity('and', 'the'))
        # Out of vocab check
        self.assertTrue(np.allclose(self.test_model.wv.similarity('nights', 'nights'), 1.0))
        self.assertEqual(self.test_model.wv.similarity('night', 'nights'), self.test_model.wv.similarity('nights', 'night'))

    def test_most_similar(self):
        # In vocab, sanity check
        self.assertEqual(len(self.test_model.wv.most_similar(positive=['the', 'and'], topn=5)), 5)
        self.assertEqual(self.test_model.wv.most_similar('the'), self.test_model.wv.most_similar(positive=['the']))
        # Out of vocab check
        self.assertEqual(len(self.test_model.wv.most_similar(['night', 'nights'], topn=5)), 5)
        self.assertEqual(self.test_model.wv.most_similar('nights'), self.test_model.wv.most_similar(positive=['nights']))

    def test_most_similar_cosmul(self):
        # In vocab, sanity check
        self.assertEqual(len(self.test_model.wv.most_similar_cosmul(positive=['the', 'and'], topn=5)), 5)
        self.assertEqual(
            self.test_model.wv.most_similar_cosmul('the'),
            self.test_model.wv.most_similar_cosmul(positive=['the']))
        # Out of vocab check
        self.assertEqual(len(self.test_model.wv.most_similar_cosmul(['night', 'nights'], topn=5)), 5)
        self.assertEqual(
            self.test_model.wv.most_similar_cosmul('nights'),
            self.test_model.wv.most_similar_cosmul(positive=['nights']))

    def test_lookup(self):
        # In vocab, sanity check
        self.assertTrue('night' in self.test_model.wv.vocab)
        self.assertTrue(np.allclose(self.test_model['night'], self.test_model[['night']]))
        # Out of vocab check
        self.assertFalse('nights' in self.test_model.wv.vocab)
        self.assertTrue(np.allclose(self.test_model['nights'], self.test_model[['nights']]))
        # Word with no ngrams in model
        self.assertRaises(KeyError, lambda: self.test_model['a!@'])

    def test_contains(self):
        # In vocab, sanity check
        self.assertTrue('night' in self.test_model.wv.vocab)
        self.assertTrue('night' in self.test_model)
        # Out of vocab check
        self.assertFalse('nights' in self.test_model.wv.vocab)
        self.assertTrue('nights' in self.test_model)
        # Word with no ngrams in model
        self.assertFalse('a!@' in self.test_model.wv.vocab)
        self.assertFalse('a!@' in self.test_model)

    def test_wm_distance(self):
        doc = ['night', 'payment']
        oov_doc = ['nights', 'forests', 'payments']
        ngrams_absent_doc = ['a!@', 'b#$']

        dist = self.test_model.wv.wmdistance(doc, oov_doc)
        self.assertNotEqual(float('inf'), dist)
        dist = self.test_model.wv.wmdistance(doc, ngrams_absent_doc)
        self.assertEqual(float('inf'), dist)

    def test_doesnt_match(self):
        oov_words = ['nights', 'forests', 'payments']
        # Out of vocab check
        for word in oov_words:
            self.assertFalse(word in self.test_model.wv.vocab)
        try:
            self.test_model.wv.doesnt_match(oov_words)
        except Exception:
            self.fail('model.doesnt_match raises exception for oov words')

    def test_cbow_hs_training(self):
        if self.ft_path is None:
            logger.info("FT_HOME env variable not set, skipping test")
            return

        model_gensim = FT_gensim(size=50, sg=0, cbow_mean=1, alpha=0.05, window=5, hs=1, negative=0,
            min_count=5, iter=5, batch_words=1000, word_ngrams=1, sample=1e-3, min_n=3, max_n=6,
            sorted_vocab=1, workers=1, min_alpha=0.0)

        lee_data = LineSentence(datapath('lee_background.cor'))
        model_gensim.build_vocab(lee_data)
        orig0 = np.copy(model_gensim.wv.vectors[0])
        model_gensim.train(lee_data, total_examples=model_gensim.corpus_count, epochs=model_gensim.epochs)
        self.assertFalse((orig0 == model_gensim.wv.vectors[0]).all())  # vector should vary after training

        sims_gensim = model_gensim.wv.most_similar('night', topn=10)
        sims_gensim_words = (list(map(lambda x: x[0], sims_gensim)))  # get similar words
        expected_sims_words = [
            u'night,',
            u'night.',
            u'rights',
            u'kilometres',
            u'in',
            u'eight',
            u'according',
            u'flights',
            u'during',
            u'comes']
        self.assertEqual(sims_gensim_words, expected_sims_words)

    def test_sg_hs_training(self):
        if self.ft_path is None:
            logger.info("FT_HOME env variable not set, skipping test")
            return

        model_gensim = FT_gensim(size=50, sg=1, cbow_mean=1, alpha=0.025, window=5, hs=1, negative=0,
            min_count=5, iter=5, batch_words=1000, word_ngrams=1, sample=1e-3, min_n=3, max_n=6,
            sorted_vocab=1, workers=1, min_alpha=0.0)

        lee_data = LineSentence(datapath('lee_background.cor'))
        model_gensim.build_vocab(lee_data)
        orig0 = np.copy(model_gensim.wv.vectors[0])
        model_gensim.train(lee_data, total_examples=model_gensim.corpus_count, epochs=model_gensim.epochs)
        self.assertFalse((orig0 == model_gensim.wv.vectors[0]).all())  # vector should vary after training

        sims_gensim = model_gensim.wv.most_similar('night', topn=10)
        sims_gensim_words = (list(map(lambda x: x[0], sims_gensim)))  # get similar words
        expected_sims_words = [
            u'night,',
            u'night.',
            u'eight',
            u'nine',
            u'overnight',
            u'crew',
            u'overnight.',
            u'manslaughter',
            u'north',
            u'flight']
        self.assertEqual(sims_gensim_words, expected_sims_words)

    def test_cbow_neg_training(self):
        if self.ft_path is None:
            logger.info("FT_HOME env variable not set, skipping test")
            return

        model_gensim = FT_gensim(size=50, sg=0, cbow_mean=1, alpha=0.05, window=5, hs=0, negative=5,
            min_count=5, iter=5, batch_words=1000, word_ngrams=1, sample=1e-3, min_n=3, max_n=6,
            sorted_vocab=1, workers=1, min_alpha=0.0)

        lee_data = LineSentence(datapath('lee_background.cor'))
        model_gensim.build_vocab(lee_data)
        orig0 = np.copy(model_gensim.wv.vectors[0])
        model_gensim.train(lee_data, total_examples=model_gensim.corpus_count, epochs=model_gensim.epochs)
        self.assertFalse((orig0 == model_gensim.wv.vectors[0]).all())  # vector should vary after training

        sims_gensim = model_gensim.wv.most_similar('night', topn=10)
        sims_gensim_words = (list(map(lambda x: x[0], sims_gensim)))  # get similar words
        expected_sims_words = [
            u'night.',
            u'night,',
            u'eight',
            u'fight',
            u'month',
            u'hearings',
            u'Washington',
            u'remains',
            u'overnight',
            u'running']
        self.assertEqual(sims_gensim_words, expected_sims_words)

    def test_sg_neg_training(self):
        if self.ft_path is None:
            logger.info("FT_HOME env variable not set, skipping test")
            return

        model_gensim = FT_gensim(size=50, sg=1, cbow_mean=1, alpha=0.025, window=5, hs=0, negative=5,
            min_count=5, iter=5, batch_words=1000, word_ngrams=1, sample=1e-3, min_n=3, max_n=6,
            sorted_vocab=1, workers=1, min_alpha=0.0)

        lee_data = LineSentence(datapath('lee_background.cor'))
        model_gensim.build_vocab(lee_data)
        orig0 = np.copy(model_gensim.wv.vectors[0])
        model_gensim.train(lee_data, total_examples=model_gensim.corpus_count, epochs=model_gensim.epochs)
        self.assertFalse((orig0 == model_gensim.wv.vectors[0]).all())  # vector should vary after training

        sims_gensim = model_gensim.wv.most_similar('night', topn=10)
        sims_gensim_words = (list(map(lambda x: x[0], sims_gensim)))  # get similar words
        expected_sims_words = [
            u'night.',
            u'night,',
            u'eight',
            u'overnight',
            u'overnight.',
            u'month',
            u'land',
            u'firm',
            u'singles',
            u'death']
        self.assertEqual(sims_gensim_words, expected_sims_words)

    def test_online_learning(self):
        model_hs = FT_gensim(sentences, size=10, min_count=1, seed=42, hs=1, negative=0)
        self.assertTrue(len(model_hs.wv.vocab), 12)
        self.assertTrue(len(model_hs.wv.ngrams), 202)
        self.assertTrue(model_hs.wv.vocab['graph'].count, 3)
        self.assertFalse('tif' in model_hs.wv.ngrams)
        model_hs.build_vocab(new_sentences, update=True)  # update vocab
        self.assertEqual(len(model_hs.wv.vocab), 14)
        self.assertTrue(len(model_hs.wv.ngrams), 271)
        self.assertTrue(model_hs.wv.vocab['graph'].count, 4)
        self.assertTrue(model_hs.wv.vocab['artificial'].count, 4)
        self.assertTrue('tif' in model_hs.wv.ngrams)  # ngram added because of the word `artificial`

    def test_online_learning_after_save(self):
        tmpf = get_tmpfile('gensim_fasttext.tst')
        model_neg = FT_gensim(sentences, size=10, min_count=0, seed=42, hs=0, negative=5)
        model_neg.save(tmpf)
        model_neg = FT_gensim.load(tmpf)
        self.assertTrue(len(model_neg.wv.vocab), 12)
        self.assertTrue(len(model_neg.wv.ngrams), 202)
        model_neg.build_vocab(new_sentences, update=True)  # update vocab
        model_neg.train(new_sentences, total_examples=model_neg.corpus_count, epochs=model_neg.epochs)
        self.assertEqual(len(model_neg.wv.vocab), 14)
        self.assertTrue(len(model_neg.wv.ngrams), 271)

    def online_sanity(self, model):
        terro, others = [], []
        for l in list_corpus:
            if 'terrorism' in l:
                terro.append(l)
            else:
                others.append(l)
        self.assertTrue(all(['terrorism' not in l for l in others]))
        model.build_vocab(others)
        model.train(others, total_examples=model.corpus_count, epochs=model.iter)
        # checks that `vectors` is different from `vectors_vocab`
        self.assertFalse(np.all(np.equal(model.wv.vectors, model.wv.vectors_vocab)))
        self.assertFalse('terrorism' in model.wv.vocab)
        self.assertFalse('orism>' in model.wv.ngrams)
        model.build_vocab(terro, update=True)  # update vocab
        self.assertTrue(model.wv.vectors_ngrams.dtype == 'float32')
        self.assertTrue('terrorism' in model.wv.vocab)
        self.assertTrue('orism>' in model.wv.ngrams)
        orig0_all = np.copy(model.wv.vectors_ngrams)
        model.train(terro, total_examples=len(terro), epochs=model.iter)
        self.assertFalse(np.allclose(model.wv.vectors_ngrams, orig0_all))
        sim = model.wv.n_similarity(['war'], ['terrorism'])
        self.assertLess(0., sim)

    @unittest.skipIf(IS_WIN32, "avoid memory error with Appveyor x32")
    def test_sg_hs_online(self):
        model = FT_gensim(sg=1, window=2, hs=1, negative=0, min_count=3, iter=1, seed=42, workers=1)
        self.online_sanity(model)

    @unittest.skipIf(IS_WIN32, "avoid memory error with Appveyor x32")
    def test_sg_neg_online(self):
        model = FT_gensim(sg=1, window=2, hs=0, negative=5, min_count=3, iter=1, seed=42, workers=1)
        self.online_sanity(model)

    @unittest.skipIf(IS_WIN32, "avoid memory error with Appveyor x32")
    def test_cbow_hs_online(self):
        model = FT_gensim(
            sg=0, cbow_mean=1, alpha=0.05, window=2, hs=1, negative=0, min_count=3, iter=1, seed=42, workers=1
        )
        self.online_sanity(model)

    @unittest.skipIf(IS_WIN32, "avoid memory error with Appveyor x32")
    def test_cbow_neg_online(self):
        model = FT_gensim(
            sg=0, cbow_mean=1, alpha=0.05, window=2, hs=0, negative=5,
            min_count=5, iter=1, seed=42, workers=1, sample=0
        )
        self.online_sanity(model)

    def test_get_vocab_word_vecs(self):
        model = FT_gensim(size=10, min_count=1, seed=42)
        model.build_vocab(sentences)
        original_vectors_vocab = np.copy(model.wv.vectors_vocab)
        model.trainables.get_vocab_word_vecs(vocabulary=model.vocabulary)
        self.assertTrue(np.all(np.equal(model.wv.vectors_vocab, original_vectors_vocab)))

    def test_persistence_word2vec_format(self):
        """Test storing/loading the model in word2vec format."""
        tmpf = get_tmpfile('gensim_fasttext_w2v_format.tst')
        model = FT_gensim(sentences, min_count=1, size=10)
        model.wv.save_word2vec_format(tmpf, binary=True)
        loaded_model_kv = Word2VecKeyedVectors.load_word2vec_format(tmpf, binary=True)
        self.assertEqual(len(model.wv.vocab), len(loaded_model_kv.vocab))
        self.assertTrue(np.allclose(model['human'], loaded_model_kv['human']))

    def test_bucket_ngrams(self):
        model = FT_gensim(size=10, min_count=1, bucket=20)
        model.build_vocab(sentences)
        self.assertEqual(model.wv.vectors_ngrams.shape, (20, 10))
        model.build_vocab(new_sentences, update=True)
        self.assertEqual(model.wv.vectors_ngrams.shape, (20, 10))


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)
    unittest.main()
