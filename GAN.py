import TransformerDiscriminator
import Generator
import tensorflow as tf
import numpy as np

train_steps = 100

# params for discriminator
NUM_LAYERS = 1
D_MODEL = 30
DFF = 60
NUM_HEADS = 1

DROPOUT_RATE = 0.1
STR_LENGTH = 9

disc_train_loss = tf.keras.metrics.Mean(name='disc_train_loss')
disc_accuracy = tf.keras.metrics.Accuracy(
    name='accuracy')

# ________________________________________

# params for generator
vocab = []
vocab_dict = {}
with open('vocab.txt', 'r') as f:
    for i, line in enumerate(f, start=1):
        word = line.split()[0]
        vocab.append(word)
        vocab_dict[word] = i

# TODO don't think this is right for me
rnn_units = 1024
embedding_dim = 256
BATCH_SIZE = 5

NUM_GENERATE = 3
gen_train_loss = tf.keras.metrics.Mean(name='gen_train_loss')
gen_accuracy = tf.keras.metrics.Accuracy(
    name='accuracy')

# ________________________________________

# params for gan
# BATCH_SIZE_GAN = 6*BATCH_SIZE
VOCAB_SIZE = len(vocab)
input_vocab_size = len(vocab)+3


discriminator = TransformerDiscriminator.Transformer(NUM_LAYERS, D_MODEL, NUM_HEADS, DFF,
                                                     input_vocab_size, input_vocab_size,
                                                     pe_input=STR_LENGTH+2,
                                                     pe_target=STR_LENGTH+2,
                                                     rate=DROPOUT_RATE)

generator = Generator.Generator(rnn_units, embedding_dim, STR_LENGTH, vocab, BATCH_SIZE)
generator.build_model()


# ________________________________________


def get_true_labels(inp):
    inp = tf.round(inp)
    labels = []
    for data in inp:

        assert data.shape[0] % 3 == 0
        piece_len = data.shape[0] // 3

        if tf.reduce_all(data[:piece_len] == 0 * piece_len) and tf.reduce_all(data[piece_len * 2:] == 1 * piece_len):
            labels.append(1)
        else:
            labels.append(0)
    return np.array(labels)


def generate_seeds():
    return np.random.uniform(low=0, high=1, size=(BATCH_SIZE, 1, STR_LENGTH, VOCAB_SIZE))


# ________________________________________


# @tf.function
def train_step(seed):

    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:

        gen_tape.watch(generator.model.trainable_variables)

        generator_data = generator.model(seed)
        true_labels = get_true_labels(generator_data)

        enc_padding_mask, combined_mask, dec_padding_mask = TransformerDiscriminator.create_masks(generator_data,
                                                                                                  generator_data, 0)

        logits, all_weights = discriminator.call(tf.round(generator_data), tf.round(generator_data),
                                                 True, enc_padding_mask, combined_mask, dec_padding_mask)

        disc_tape.watch(discriminator.trainable_variables)
        print('`logits` has type {0}'.format(type(logits)))

        disc_loss = tf.keras.losses.binary_crossentropy(true_labels, logits, from_logits=False)
        gen_loss = generator.loss_object(1 - true_labels, logits)

        disc_gradients = disc_tape.gradient(disc_loss, discriminator.trainable_variables)
        gen_gradients = gen_tape.gradient(gen_loss, generator.model.trainable_variables)

        TransformerDiscriminator.optimizer.apply_gradients(zip(disc_gradients, discriminator.trainable_variables))
        generator.optimizer.apply_gradients(zip(gen_gradients, generator.model.trainable_variables))

        disc_train_loss.update_state(disc_loss)
        gen_train_loss.update_state(gen_loss)

    predictions = tf.round(tf.nn.sigmoid(logits))

    disc_accuracy.update_state(true_labels, predictions)
    gen_accuracy.update_state(1 - true_labels, predictions)


def train(epochs):
    for epoch in range(epochs):
        seed = generate_seeds()
        for (batch, seed) in enumerate(seed):
            train_step(seed)
        print('Epoch {} finished'.format(epoch))


train(train_steps)


