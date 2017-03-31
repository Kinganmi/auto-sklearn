# -*- encoding: utf-8 -*-
import copy
import json
import multiprocessing
import os
import shutil
import sys
import unittest
import unittest.mock

import numpy as np

this_directory = os.path.dirname(__file__)
sys.path.append(this_directory)
from evaluation_util import get_dataset_getters, BaseEvaluatorTest, \
    get_multiclass_classification_datamanager
from autosklearn.constants import *
from autosklearn.evaluation import TestEvaluator
# Otherwise nosetests thinks this is a test to run...
from autosklearn.evaluation import eval_t, get_last_result
from autosklearn.util.pipeline import get_configuration_space
from autosklearn.util import Backend
from autosklearn.metrics import accuracy, r2, f1_macro

N_TEST_RUNS = 3


class Dummy(object):
    pass


class TestEvaluator_Test(BaseEvaluatorTest, unittest.TestCase):
    _multiprocess_can_split_ = True

    def test_datasets(self):
        for getter in get_dataset_getters():
            testname = '%s_%s' % (os.path.basename(__file__).
                                  replace('.pyc', '').replace('.py', ''),
                                  getter.__name__)

            with self.subTest(testname):
                backend_mock = unittest.mock.Mock(spec=Backend)
                backend_mock.get_model_dir.return_value = 'dutirapbdxvltcrpbdlcatepdeau'
                D = getter()
                D_ = copy.deepcopy(D)
                y = D.data['Y_train']
                if len(y.shape) == 2 and y.shape[1] == 1:
                    D_.data['Y_train'] = y.flatten()
                metric_lookup = {MULTILABEL_CLASSIFICATION: f1_macro,
                                 BINARY_CLASSIFICATION: accuracy,
                                 MULTICLASS_CLASSIFICATION: accuracy,
                                 REGRESSION: r2}
                queue_ = multiprocessing.Queue()

                evaluator = TestEvaluator(D_, backend_mock, queue_,
                                          metric=metric_lookup[D.info['task']])

                evaluator.fit_predict_and_loss()
                duration, result, seed, run_info, status = evaluator.queue.get(timeout=1)
                self.assertTrue(np.isfinite(result))


class FunctionsTest(unittest.TestCase):
    def setUp(self):
        self.queue = multiprocessing.Queue()
        self.configuration = get_configuration_space(
            {'task': MULTICLASS_CLASSIFICATION,
             'is_sparse': False}).get_default_configuration()
        self.data = get_multiclass_classification_datamanager()
        self.tmp_dir = os.path.join(os.path.dirname(__file__),
                                    '.test_cv_functions')
        self.backend = unittest.mock.Mock(spec=Backend)
        self.dataset_name = json.dumps({'dataset_name': 'test'})

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_dir)
        except Exception:
            pass

    def test_eval_test(self):
        eval_t(queue=self.queue,
               backend=self.backend,
               config=self.configuration,
               data=self.data,
               metric=accuracy,
               seed=1, num_run=1, subsample=None,
               all_scoring_functions=False, output_y_hat_optimization=False,
               include=None, exclude=None, disable_file_output=False,
               instance=self.dataset_name)
        info = get_last_result(self.queue)
        self.assertAlmostEqual(info[1], 0.04)
        self.assertEqual(info[2], 1)
        self.assertNotIn('bac_metric', info[3])

    def test_eval_test_all_loss_functions(self):
        eval_t(queue=self.queue,
               backend=self.backend,
               config=self.configuration,
               data=self.data,
               metric=accuracy,
               seed=1, num_run=1, subsample=None,
               all_scoring_functions=True, output_y_hat_optimization=False,
               include=None, exclude=None, disable_file_output=False,
               instance=self.dataset_name)
        info = get_last_result(self.queue)
        fixture = {'f1': 0.0396930946292,
                   'accuracy': 0.04,
                   'log_loss': 1.1274919837,
                   'precision': 0.0355555555556,
                   'recall': 0.04,
                   'num_run': -1}
        rval = {i.split(':')[0]: float(i.split(':')[1]) for i in info[3].split(';')}
        for key, value in fixture.items():
            self.assertAlmostEqual(rval[key], fixture[key], msg=key)
        self.assertEqual(len(rval), len(fixture) + 1, msg=rval)
        self.assertIn('duration', rval)
        self.assertAlmostEqual(info[1], 0.04)
        self.assertEqual(info[2], 1)
