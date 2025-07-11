import tensorflow as tf
from tensorflow.keras import backend as K
import numpy as np


def combined_loss(y_true, y_pred, k_mixture, mse_weight, mdn_weight):
    alpha = y_pred[..., :k_mixture]
    mu = y_pred[..., k_mixture:2 * k_mixture]
    sigma = y_pred[..., 2 * k_mixture:]

    y_true_r = K.reshape(y_true, (tf.shape(y_pred)[0], tf.shape(y_pred)[1], 1))
    y_true_r = K.cast(y_true_r, mu.dtype)

    sigma = K.clip(sigma, K.epsilon(), 1e6)

    pi = tf.constant(np.pi, dtype=mu.dtype)
    prob = K.exp(-0.5 * K.square((y_true_r - mu) / sigma)) / (sigma * K.sqrt(2 * pi))
    mdn_loss_val = -K.mean(K.log(K.sum(alpha * prob, axis=-1) + K.epsilon()))

    pred_mean = K.sum(alpha * mu, axis=-1)
    mse_loss_val = K.mean(K.square(pred_mean - K.squeeze(y_true_r, axis=-1)))

    return mse_weight * mse_loss_val + mdn_weight * mdn_loss_val

def get_custom_loss(k_mixture, mse_weight, mdn_weight):
    def custom_loss(y_true, y_pred):
        return combined_loss(y_true, y_pred, k_mixture, mse_weight, mdn_weight)

    custom_loss.__name__ = 'custom_combined_loss'
    return custom_loss

def _get_pred_mean(y_pred, k_mixture):
    alpha = y_pred[..., :k_mixture]
    mu = y_pred[..., k_mixture:2 * k_mixture]
    return tf.reduce_sum(alpha * mu, axis=-1)


def _reshape_true(y_true, pred_mean):
    y_true_r = tf.reshape(y_true, tf.shape(pred_mean))
    return tf.cast(y_true_r, pred_mean.dtype)


def mu_rmse(y_true, y_pred, k_mixture=3):
    pred_mean = _get_pred_mean(y_pred, k_mixture)
    y_true_r = _reshape_true(y_true, pred_mean)
    return K.sqrt(K.mean(K.square(pred_mean - y_true_r)))


def mae(y_true, y_pred, k_mixture=3):
    pred_mean = _get_pred_mean(y_pred, k_mixture)
    y_true_r = _reshape_true(y_true, pred_mean)
    return tf.reduce_mean(tf.abs(pred_mean - y_true_r))


def r_squared(y_true, y_pred, k_mixture=3):
    pred_mean = _get_pred_mean(y_pred, k_mixture)
    y_true_r = _reshape_true(y_true, pred_mean)
    ss_res = tf.reduce_sum(tf.square(y_true_r - pred_mean))
    ss_tot = tf.reduce_sum(tf.square(y_true_r - tf.reduce_mean(y_true_r)))
    return (1 - ss_res / (ss_tot + K.epsilon()))


def smape(y_true, y_pred, k_mixture=3):
    pred_mean = _get_pred_mean(y_pred, k_mixture)
    y_true_r = _reshape_true(y_true, pred_mean)
    numerator = tf.abs(pred_mean - y_true_r)
    denominator = tf.abs(y_true_r) + tf.abs(pred_mean)
    return tf.reduce_mean(2.0 * numerator / tf.maximum(denominator, K.epsilon())) * 100.0