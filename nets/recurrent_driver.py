

import recurrent_network
import learning_methods


file_name ="/home/lie/lol.txt"

lang = recurrent_network.compute_language(file_name)


hl_size = 100
num_hl  = 2
max_time_step = 25

net = recurrent_network.RNNetwork(\
                hl_size, \
                num_hl,  \
                max_time_step, \
                lang \
)

epochs = 100
eta=1
learning_method = learning_methods.AdaGrad(eta)

net.no_batch_learn( \
                file_name, \
                epochs, \
                learning_method, \
)
