#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import glob
import os

import numpy as np

import infer


def build_train_id_to_filenames():
    lines = [line.rstrip('\n') for line in open(infer.TRAIN_DICT_DATA_PATH)]
    id_to_filenames = {}
    for line in lines:
        filename, class_id = line.split()
        if class_id not in id_to_filenames:
            id_to_filenames[class_id] = []
        id_to_filenames[class_id].append(filename)
    return id_to_filenames


def build_valid_id_to_filenames():
    lines = [line.rstrip('\n') for line in open(infer.VALID_DICT_DATA_PATH)]
    id_to_filenames = {}
    for line in lines:
        l = line.split()
        id = l[0]
        id_to_filenames[id] = []
        for filename in l[1:]:
            id_to_filenames[id].append(filename)

    return id_to_filenames


def build_train_feature_matrix_mean():
    filename_to_id = infer.build_train_dict()
    npz_id_to_features_list = {}
    for npz in glob.glob(infer.TRAIN_NPZ_PATH):
        head, tail = os.path.split(npz)
        mp4_filename, npz_ext = os.path.splitext(tail)
        # print(mp4_filename)

        features = np.load(npz)
        features = features.f.arr_0
        class_id = filename_to_id[mp4_filename]
        if class_id not in npz_id_to_features_list:
            npz_id_to_features_list[class_id] = []
        npz_id_to_features_list[class_id].append(features)

    feature_matrix = []
    row_index = 0
    row_index_to_id = {}
    for k, v in npz_id_to_features_list.iteritems():
        features = np.concatenate(tuple(v), axis=0)
        feature = np.mean(features, axis=0)
        feature_matrix.append([feature])
        row_index_to_id[row_index] = (k, len(v))
        row_index += 1

    # for debug
    for i in range(1, 575):
        if not str(i) in npz_id_to_features_list:
            print("** id has no features: ", i)
    print("id to features list:", len(npz_id_to_features_list))

    return np.concatenate(tuple(feature_matrix), axis=0), row_index_to_id


def calc_mean_average_precision():
    feature_matrix, row_index_to_id = build_train_feature_matrix_mean()
    print(len(row_index_to_id))
    feature_matrix = feature_matrix.T

    row_to_filename = []
    sim_list = []
    for npz in glob.glob(infer.VALID_NPZ_PATH):
        head, tail = os.path.split(npz)
        mp4_filename, npz_ext = os.path.splitext(tail)

        row_to_filename.append(mp4_filename)

        features = np.load(npz)
        features = features.f.arr_0

        # sim[i] == class_i cos similarity
        sim = np.mean(np.dot(features, feature_matrix), axis=0)
        sim_list.append([sim])

    # sim_matrix[i, j] == file_i cos similarity to class_j
    sim_matrix = np.concatenate(tuple(sim_list), axis=0)
    print("sim matrix shape: ", sim_matrix.shape)
    print("sim matrix max:{0}, min:{1}".format(sim_matrix.max(),
                                               sim_matrix.min()))

    # calc class_i average precision
    filename_to_id = infer.build_valid_dict()
    class_to_ap = {}
    valid_id_to_filenames = build_valid_id_to_filenames()
    for i in range(sim_matrix.shape[1]):
        class_id, _ = row_index_to_id[i]
        gt_count = len(valid_id_to_filenames[class_id])
        if gt_count > 100:
            gt_count = 100
        confidence = sim_matrix[:, i]

        ap = calc_ap(class_id, confidence, filename_to_id, gt_count,
                     row_to_filename)
        class_to_ap[class_id] = ap
        # print(class_to_ap[class_id])

    mean_ap = 0.0
    for ap in class_to_ap.values():
        mean_ap += ap
    mean_ap = mean_ap / len(class_to_ap)
    return mean_ap


def calc_ap(class_id, confidence, filename_to_id, gt_count,
            row_to_filename):
    # sort descending order
    #print(class_id, gt_count)
    arg_sort = np.argsort(-confidence)
    position = 1
    hit_count = 1
    precision = []
    for index in arg_sort:
        filename = row_to_filename[index]
        id = filename_to_id[filename]
        if id == class_id:
            precision.append(hit_count / position)
            hit_count += 1
        position += 1
        if position > gt_count:
            return np.sum(np.array(precision)) / gt_count


def infer_2():
    valid_dict = infer.build_valid_dict()
    feature_matrix, row_index_to_id = build_train_feature_matrix_mean()
    feature_matrix = feature_matrix.T

    total = 0
    hit = 0

    for npz in glob.glob(infer.VALID_NPZ_PATH):
        head, tail = os.path.split(npz)
        mp4_filename, npz_ext = os.path.splitext(tail)

        features = np.load(npz)
        features = features.f.arr_0
        assert (len(features.shape) == 2)

        sim = np.dot(features, feature_matrix)
        sim = np.sum(sim, axis=0)
        index = np.argmax(sim)

        predict_id = row_index_to_id[index][0]
        ground_truth = valid_dict[mp4_filename]
        if predict_id == ground_truth:
            hit += 1
        total += 1

    print(
        'hit: {0}, total: {1}, precision: {2}'.format(hit, total, hit / total))


if __name__ == "__main__":
    infer_2()
    print("mean average precision: ", calc_mean_average_precision())
